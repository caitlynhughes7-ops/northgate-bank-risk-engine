from datetime import date
from pathlib import Path

import pytest

from ecl.config import table
from ecl.engine import run
from ecl.period_dates import PeriodDates, UnsupportedPeriodError, period_dates


def test_202409_preserves_reporting_period_and_sas_serial():
    result = period_dates("202409")
    assert result.RPT_DT == "202409"
    assert isinstance(result.RPT_DT, str)
    assert result.RPT_DT_SAS == date(2024, 9, 30)
    assert result.RPT_DT_SAS_SERIAL == 23649
    assert result.PRIOR_YYYYMM == "202408"
    assert isinstance(result.PRIOR_YYYYMM, str)
    assert len(result.PRIOR_YYYYMM) == 6


def test_period_values_remain_distinct_types():
    result = period_dates("202409")
    assert isinstance(result, PeriodDates)
    assert type(result.RPT_DT) is str
    assert type(result.RPT_DT_SAS) is date
    assert type(result.RPT_DT_SAS_SERIAL) is int
    assert type(result.PRIOR_YYYYMM) is str


@pytest.mark.parametrize(
    ("period", "reporting", "prior"),
    [
        ("202412", date(2024, 12, 31), "202411"),
        ("202501", date(2025, 1, 31), "202412"),
    ],
)
def test_december_and_january_rollover(period, reporting, prior):
    result = period_dates(period)
    assert result.RPT_DT_SAS == reporting
    assert result.PRIOR_YYYYMM == prior


@pytest.mark.parametrize(
    ("period", "reporting", "prior"),
    [
        ("202402", date(2024, 2, 29), "202401"),
        ("202302", date(2023, 2, 28), "202301"),
        ("202403", date(2024, 3, 31), "202402"),
    ],
)
def test_february_end_of_month_and_prior_period(period, reporting, prior):
    result = period_dates(period)
    assert result.RPT_DT_SAS == reporting
    assert result.PRIOR_YYYYMM == prior


def test_prior_period_crosses_months_of_differing_length():
    result = period_dates("202405")
    assert result.RPT_DT_SAS == date(2024, 5, 31)
    assert result.PRIOR_YYYYMM == "202404"


def test_whitespace_is_stripped_but_extra_characters_are_preserved():
    result = period_dates(" 2024091 ")
    assert result.RPT_DT == "2024091"
    assert result.RPT_DT_SAS == date(2024, 9, 30)
    assert result.PRIOR_YYYYMM == "202408"


@pytest.mark.parametrize("period", ["20240", "20x409", "202400", "202413"])
def test_malformed_or_out_of_range_period_raises_unsupported_period(period):
    with pytest.raises(UnsupportedPeriodError, match="unverified"):
        period_dates(period)


def test_period_date_rules_are_verbatim_legacy_configuration():
    rules_path = Path(__file__).parents[2] / "config/rules/period_dates.csv"
    assert rules_path.exists()
    assert dict(zip(table("period_dates.csv").PARAM, table("period_dates.csv").VALUE)) == {
        "sas_epoch": "1960-01-01",
        "month_alignment": "e",
        "prior_month_offset": "-1",
        "prior_period_format": "yymmn6",
        "period_year_start": "1",
        "period_year_length": "4",
        "period_month_start": "5",
        "period_month_length": "2",
    }


def test_engine_emits_legacy_period_note_and_keeps_output_unchanged(caplog):
    with caplog.at_level("INFO", logger="ecl.engine"):
        output, result = run("202409", write=False)
    assert output.equals(run("202409", write=False)[0])
    assert result.equals(run("202409", write=False)[1])
    assert "NOTE: [ECL] reporting date 23649 prior period 202408" in caplog.text
