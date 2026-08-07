import pandas as pd

from ecl.pd_model import pd_pit, term_structure


def test_float_rating_grade_preserves_numeric_masterscale():
    exposures = pd.DataFrame(
        {
            "RATING_GRADE": pd.Series([15.0, None], dtype="float64"),
            "ARREARS_BUCKET": ["0", "0"],
            "FORBEARANCE_FL": [False, False],
            "DEFAULT_FL": [False, False],
        }
    )
    scenarios = pd.DataFrame(
        {
            "SCENARIO": ["BASE"],
            "GDP_SHOCK": [0.0],
            "UNEMP_RATE": [4.2],
        }
    )
    result = pd_pit(exposures, scenarios)
    assert result.PD_GRADE.iloc[0] == 1.0
    assert result.PD_GRADE.iloc[1] == 0.041


def test_missing_remaining_term_uses_configured_cap():
    exposures = pd.DataFrame(
        {
            "ACCOUNT_ID": ["A"],
            "PD_12M": [0.1],
            "REMAIN_TERM_M": [None],
            "EIR": [0.1],
            "SEGMENT": ["PERSONAL_LOAN"],
        }
    )
    curve, _ = term_structure(exposures)
    assert curve["T"].max() == 120
    assert len(curve) == 120
