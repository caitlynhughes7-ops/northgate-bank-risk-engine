from datetime import datetime
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from ecl.engine import run
import ecl.recon as recon_module
from ecl.recon import best12, recon_controls


NOW = datetime(2026, 8, 6, 19, 46, 1)
ROOT = Path(__file__).resolve().parents[2]


def _frames(stage=(1, 2), drawn=(100.0, 200.0), ead=(110.0, 210.0), ecl=(1.0, 2.0)):
    tape = pd.DataFrame({"DRAWN_BAL": drawn})
    account = pd.DataFrame({"EAD": ead, "ECL": ecl, "STAGE": stage})
    return tape, account


def test_recon_step_is_first_and_control_note_is_exact():
    # Legacy macro logs its step before querying and writing the control NOTE.
    tape, account = _frames()
    lines = []
    recon_controls(tape, account, now=NOW, emit=lines.append)
    assert lines[0] == "NOTE: [ECL] recon_controls  (06AUG2026:19:46:01)"
    assert lines[1] == "NOTE: [ECL] control drawn=         300 ead=         320 ecl=           3"


def test_sas_sum_ignores_missing_values():
    # PROC SQL SUM ignores missing values when at least one value is present.
    tape, account = _frames(drawn=(100.0, np.nan), ead=(np.nan, 210.0), ecl=(1.0, np.nan))
    result = recon_controls(tape, account, now=NOW, emit=lambda _: None)
    assert (result.drawn, result.ead, result.ecl) == (100.0, 210.0, 1.0)


def test_empty_and_all_missing_sums_render_sas_missing():
    # PROC SQL SUM returns SAS missing, rather than pandas' empty sum of zero.
    tape = pd.DataFrame({"DRAWN_BAL": pd.Series(dtype=float)})
    account = pd.DataFrame({"EAD": [np.nan], "ECL": [np.nan], "STAGE": [1]})
    lines = []
    recon_controls(tape, account, now=NOW, emit=lines.append)
    assert "drawn=           ." in lines[1]
    assert "ead=           ." in lines[1]
    assert "ecl=           ." in lines[1]
    assert "0" not in lines[1]


def test_null_stage_logs_error_and_returns_normally():
    # %put ERROR: is non-aborting; only %assert_rows aborts in the legacy flow.
    tape, account = _frames(stage=(np.nan, 2))
    lines = []
    result = recon_controls(tape, account, now=NOW, emit=lines.append)
    assert result.null_stage_count == 1
    assert lines[2] == "ERROR: [ECL]            1 exposures with null stage"


def test_zero_null_stages_emit_no_error():
    # The legacy conditional emits no ERROR line when count is zero.
    tape, account = _frames(stage=(0, ""))
    lines = []
    recon_controls(tape, account, now=NOW, emit=lines.append)
    assert len(lines) == 2


def test_only_numeric_nan_stages_count_as_missing():
    # SAS numeric missing is not zero, empty text, or the literal NULL string.
    tape, account = _frames(
        stage=(np.nan, 0, "", "NULL"),
        drawn=(100, 200, 300, 400),
        ead=(100, 200, 300, 400),
        ecl=(1, 2, 3, 4),
    )
    result = recon_controls(tape, account, now=NOW, emit=lambda _: None)
    assert result.null_stage_count == 1


def test_none_and_pandas_missing_stages_count_as_missing():
    # SAS missing includes None-like values in an object-dtype staging column.
    tape, account = _frames(
        stage=(None, pd.NA, 0, "", "NULL"),
        drawn=(100, 200, 300, 400, 500),
        ead=(100, 200, 300, 400, 500),
        ecl=(1, 2, 3, 4, 5),
    )
    result = recon_controls(tape, account, now=NOW, emit=lambda _: None)
    assert result.null_stage_count == 2


def test_recon_controls_writes_no_file_or_dataset(tmp_path, monkeypatch):
    # The legacy unit is log-only and creates neither a dataset nor a file.
    monkeypatch.chdir(tmp_path)
    tape, account = _frames()
    assert recon_controls(tape, account, now=NOW, emit=lambda _: None) is not None
    assert list(tmp_path.rglob("*")) == []


def test_recon_tolerance_is_loaded_but_not_applied():
    # SC-10: RECON_TOL is loaded from the environment but never compared.
    tape, account = _frames()
    for env, expected in (("uat", 0.005), ("prod", 0.0005)):
        lines = []
        result = recon_controls(tape, account, env=env, now=NOW, emit=lines.append)
        assert result.recon_tolerance_loaded == expected
        assert result.recon_tolerance_applied is False
        assert not any(token in "\n".join(lines) for token in ("PASS", "FAIL", "comparison"))


def test_unknown_env_keeps_log_only_control_non_failing():
    # Missing environment configuration cannot abort the legacy log-only unit.
    tape, account = _frames()
    lines = []
    result = recon_controls(tape, account, env="unknown", now=NOW, emit=lines.append)
    assert result.recon_tolerance_loaded is None
    assert len(lines) == 2


def test_missing_recon_tolerance_keeps_log_only_control_non_failing(monkeypatch):
    # An environment without RECON_TOL still emits both legacy log lines.
    tape, account = _frames()

    def missing_tolerance(_):
        raise ValueError("RECON_TOL is not defined")

    monkeypatch.setattr(recon_module, "env_recon_tolerance", missing_tolerance)
    lines = []
    result = recon_controls(tape, account, env="uat", now=NOW, emit=lines.append)
    assert result.recon_tolerance_loaded is None
    assert len(lines) == 2


def test_shuffled_rows_have_identical_control_line():
    # Control totals are aggregate SQL results and do not depend on row order.
    tape, account = _frames(drawn=(100, 200, 300), ead=(300, 200, 100), ecl=(3, 2, 1), stage=(1, 2, 3))
    first, second = [], []
    recon_controls(tape, account, now=NOW, emit=first.append)
    recon_controls(tape.iloc[::-1], account.iloc[::-1], now=NOW, emit=second.append)
    assert first[1] == second[1]


def test_best12_cases():
    # BEST12. retains width, rounds values that cannot fit, and uses E notation.
    # Exact SAS E-notation rendering is an untested assumption, unreachable by realistic control totals.
    assert best12(19) == "          19"
    assert best12(25392847.5599999998) == " 25392847.56"
    assert best12(-12.34) == "      -12.34"
    assert best12(None) == "           ."
    assert best12(1e100) == "      1E+100"


def test_best12_compacts_rounded_trailing_zeros():
    # BEST12. rounds to fit and does not retain meaningless fixed-point zeros.
    assert best12(1234567.89999999) == "   1234567.9"
    assert best12(364013988.00000006) == "   364013988"
    assert best12(12345678900.4) == " 12345678900"
    assert best12(20000000000.5) == " 20000000001"


def test_best12_uses_exponent_for_small_magnitudes():
    # BEST12. switches to E notation when fixed point loses significant digits.
    assert best12(1e-15) == "       1E-15"
    assert best12(1.23e-10) == "    1.23E-10"


def test_engine_publishes_before_controls(tmp_path, capsys):
    # EO-05: controls run after disclosure and GL publication, not before it.
    shutil.copytree(ROOT / "data/input", tmp_path / "data/input")
    run("202409", tmp_path, write=True)
    lines = capsys.readouterr().out.splitlines()
    export_index = next(index for index, line in enumerate(lines) if " export_disclosure " in line)
    assert export_index < next(
        index for index, line in enumerate(lines) if " control drawn=" in line
    )
    assert (tmp_path / "data/output/ecl_by_segment_202409.csv").exists()
    assert (tmp_path / "data/output/ECL_GL_FEED_202409.txt").exists()
