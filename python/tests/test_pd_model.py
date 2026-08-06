import pandas as pd

from ecl.pd_model import pd_pit


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
