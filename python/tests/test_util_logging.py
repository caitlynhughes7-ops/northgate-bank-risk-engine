from datetime import datetime
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from ecl.config import table
from ecl.engine import run
from ecl.clean import clean
from ecl.io import load_period
from ecl.util_logging import EclAbort, assert_rows, configured_minrows, format_datetime20, log_step

ROOT = Path(__file__).resolve().parents[2]


def test_log_step_formats_complete_line_with_message():
    lines = []
    log_step("load_loan_tape", msg="period 202409", now=datetime(2026, 8, 6, 19, 46, 1), emit=lines.append)
    assert lines == ["NOTE: [ECL] load_loan_tape period 202409 (06AUG2026:19:46:01)"]


def test_log_step_omitted_message_preserves_double_space():
    lines = []
    log_step("clean_loan_tape", now=datetime(2026, 8, 6, 19, 46, 1), emit=lines.append)
    assert lines[0] == "NOTE: [ECL] clean_loan_tape  (06AUG2026:19:46:01)"


@pytest.mark.parametrize(
    ("month", "abbreviation"),
    [(1, "JAN"), (2, "FEB"), (3, "MAR"), (4, "APR"), (5, "MAY"), (6, "JUN"), (7, "JUL"), (8, "AUG"), (9, "SEP"), (10, "OCT"), (11, "NOV"), (12, "DEC")],
)
def test_format_datetime20_uses_uppercase_english_months(month, abbreviation):
    value = format_datetime20(datetime(2026, month, 6, 0, 0, 0))
    assert value == f"06{abbreviation}2026:00:00:00"
    assert len(value) == 18
    assert not value.startswith(" ")


def test_format_datetime20_renders_midnight_single_digit_day():
    assert format_datetime20(datetime(2026, 1, 1, 0, 0, 0)) == "01JAN2026:00:00:00"


def test_format_datetime20_truncates_fractional_seconds():
    assert format_datetime20(datetime(2026, 8, 6, 19, 46, 1, 999999)) == "06AUG2026:19:46:01"


def test_log_step_always_emits_note_severity(capsys):
    log_step("ERROR step", msg="ERROR details", now=datetime(2026, 8, 6, 19, 46, 1))
    line = capsys.readouterr().out
    assert line.startswith("NOTE:")
    assert not line.startswith("ERROR")


def test_log_step_trims_macro_parameter_blanks_but_preserves_internal_spacing():
    lines = []
    log_step("  step   with  spaces  ", msg="  message   with  spaces  ", now=datetime(2026, 8, 6, 19, 46, 1), emit=lines.append)
    assert lines[0] == "NOTE: [ECL] step   with  spaces message   with  spaces (06AUG2026:19:46:01)"


def test_log_step_injected_timestamp_is_deterministic():
    first = []
    second = []
    timestamp = datetime(2026, 8, 6, 19, 46, 1)
    log_step("step", msg="message", now=timestamp, emit=first.append)
    log_step("step", msg="message", now=timestamp, emit=second.append)
    assert first == second


def test_log_step_default_sink_writes_one_line_to_stdout(capsys):
    log_step("step", now=datetime(2026, 8, 6, 19, 46, 1))
    assert capsys.readouterr().out == "NOTE: [ECL] step  (06AUG2026:19:46:01)\n"


def test_engine_logs_legacy_steps_in_driver_order(capsys):
    run("202409", ROOT)
    names = [line.split(" ")[2] for line in capsys.readouterr().out.splitlines()]
    assert names == [
        "load_loan_tape",
        "stg.loan_tape",
        "clean_loan_tape",
        "stg.tape_clean",
        "map_product_hierarchy",
        "derive_arrears",
        "ead_ccf",
        "pd_pit",
        "pd_term_structure",
        "lgd_secured",
        "lgd_unsecured",
        "staging_sicr",
        "fli_overlay",
        "discount_eir",
        "ecl_calc",
        "aggregate_reporting",
        "export_disclosure",
    ]


def test_assert_rows_emits_exact_note_line_on_pass():
    lines = []
    assert_rows(pd.DataFrame(index=range(2)), "stg.loan_tape", 2, emit=lines.append)
    assert lines == ["NOTE: [ECL] stg.loan_tape row count 2"]


def test_assert_rows_emits_exact_error_line_and_aborts():
    lines = []
    with pytest.raises(EclAbort):
        assert_rows(pd.DataFrame(index=range(1)), "stg.tape_clean", 2, emit=lines.append)
    assert lines == ["ERROR: [ECL] stg.tape_clean has 1 rows, expected at least 2"]
    assert lines[0].startswith("ERROR")


@pytest.mark.parametrize(("count", "minimum"), [(2, 2), (1, 2), (0, 0)])
def test_assert_rows_uses_strict_explicit_threshold(count, minimum):
    lines = []
    if count < minimum:
        with pytest.raises(EclAbort):
            assert_rows(pd.DataFrame(index=range(count)), "test", minimum, emit=lines.append)
    else:
        assert_rows(pd.DataFrame(index=range(count)), "test", minimum, emit=lines.append)
    assert lines[0].startswith("ERROR") is (count < minimum)


def test_assert_rows_uses_configured_default_threshold():
    params = dict(zip(table("logging.csv").PARAM, table("logging.csv").VALUE))
    assert int(params["assert_rows_default_minrows"]) == 1
    lines = []
    assert_rows(pd.DataFrame(index=range(1)), "test", emit=lines.append)
    assert lines == ["NOTE: [ECL] test row count 1"]
    with pytest.raises(EclAbort, match="test has 0 rows, expected at least 1"):
        assert_rows(pd.DataFrame(index=range(0)), "test", emit=lines.append)


def test_configured_live_row_count_thresholds_match_legacy_values():
    assert configured_minrows("stg.loan_tape") == 100
    assert configured_minrows("stg.tape_clean") == 100


def test_assert_rows_counts_duplicate_and_all_nan_rows():
    frame = pd.DataFrame({"value": [float("nan"), float("nan"), 1, 1]})
    lines = []
    assert_rows(frame, "test", 4, emit=lines.append)
    assert lines == ["NOTE: [ECL] test row count 4"]


def test_load_period_asserts_before_collateral_is_read(tmp_path, capsys):
    input_dir = tmp_path / "data/input"
    input_dir.mkdir(parents=True)
    pd.DataFrame({"ACCOUNT_ID": [1] * 99}).to_csv(input_dir / "loan_tape_short.csv", index=False)
    with pytest.raises(EclAbort):
        load_period(tmp_path, "short")
    assert capsys.readouterr().out.splitlines()[-1] == "ERROR: [ECL] stg.loan_tape has 99 rows, expected at least 100"


def test_abort_halts_engine_before_output_file_is_written(tmp_path):
    input_dir = tmp_path / "data/input"
    input_dir.mkdir(parents=True)
    pd.DataFrame({"ACCOUNT_ID": [1] * 99}).to_csv(input_dir / "loan_tape_short.csv", index=False)
    with pytest.raises(EclAbort):
        run("short", tmp_path)
    output_dir = tmp_path / "data/output"
    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_clean_asserts_configured_threshold_and_legacy_name(capsys):
    frame = pd.DataFrame(
        {
            "ACCOUNT_ID": range(99),
            "DPD": ["0"] * 99,
            "FORBEARANCE": ["N"] * 99,
            "WATCHLIST": ["N"] * 99,
            "DEFAULT_IND": ["N"] * 99,
            "IO_FLAG": ["N"] * 99,
            "MONTHLY_PAYMENT": [1] * 99,
            "EIR": [0.1] * 99,
            "DRAWN_BAL": [1] * 99,
            "UNDRAWN": [0] * 99,
        }
    )
    with pytest.raises(EclAbort):
        clean(frame)
    assert capsys.readouterr().out.splitlines()[-1] == "ERROR: [ECL] stg.tape_clean has 99 rows, expected at least 100"


def test_cli_returns_nonzero_on_assert_abort(monkeypatch):
    from ecl import cli

    monkeypatch.setattr(cli, "run", lambda period: (_ for _ in ()).throw(EclAbort()))
    monkeypatch.setattr(sys, "argv", ["ecl", "--period", "short"])
    assert cli.main() == 1


def test_cli_process_exits_nonzero_on_assert_abort():
    code = (
        f"import sys; sys.path.insert(0, {str(ROOT / 'python')!r}); "
        "import ecl.cli; from ecl.util_logging import EclAbort; "
        "ecl.cli.run = lambda period: (_ for _ in ()).throw(EclAbort()); "
        "sys.argv = ['ecl', '--period', 'short']; "
        "raise SystemExit(ecl.cli.main())"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode != 0
