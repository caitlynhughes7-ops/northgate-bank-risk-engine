import json

import pandas as pd

from tools.regression_harness import comparison_rows, compare

def test_parity_202409():
    assert compare("202409")


def test_parity_artifact_is_valid_json_and_one_sided_rows_are_failures():
    expected = pd.DataFrame(
        {"SEGMENT": ["A"], "STAGE": [1], "N_EXPOSURES": [1], "TOTAL_EAD": [10.0], "TOTAL_ECL": [1.0], "COVERAGE": [0.1]}
    )
    actual = pd.DataFrame(
        {"SEGMENT": ["B"], "STAGE": [1], "N_EXPOSURES": [1], "TOTAL_EAD": [10.0], "TOTAL_ECL": [1.0], "COVERAGE": [0.1]}
    )
    rows = comparison_rows(expected, actual)
    missing = next(row for row in rows if row["SEGMENT"] == "A")
    assert missing["TOTAL_EAD"]["expected"] == 10.0
    assert missing["TOTAL_EAD"]["actual"] is None
    assert missing["TOTAL_EAD"]["within_tolerance"] is False
    assert missing["COVERAGE"]["within_tolerance"] is None
    with open("data/output/parity_202409.json") as artifact:
        json.load(artifact)
