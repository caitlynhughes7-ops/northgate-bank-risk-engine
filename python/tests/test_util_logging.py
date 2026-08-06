from datetime import datetime
from pathlib import Path

import pytest

from ecl.engine import run
from ecl.util_logging import format_datetime20, log_step

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
    names = [
        line.split(" ")[2]
        for line in capsys.readouterr().out.splitlines()
        if line.split(" ")[2] in {
            "load_loan_tape",
            "clean_loan_tape",
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
            "recon_controls",
        }
    ]
    assert names == [
        "load_loan_tape",
        "clean_loan_tape",
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
        "recon_controls",
    ]
