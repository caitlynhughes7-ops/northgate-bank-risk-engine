import pandas as pd

from ecl.board_pack import board_pack
from tools.regression_harness import board_pack_comparison_rows


def test_all_missing_group_is_missing_not_zero():
    aggregate = pd.DataFrame(
        {"SEGMENT": ["A", "A"], "TOTAL_EAD": [None, None], "TOTAL_ECL": [None, None]}
    )
    result = board_pack(aggregate)
    assert pd.isna(result.loc[0, "EAD"])
    assert pd.isna(result.loc[0, "ECL"])


def test_missing_segment_group_is_retained():
    aggregate = pd.DataFrame(
        {"SEGMENT": [None, "A"], "TOTAL_EAD": [1.0, 2.0], "TOTAL_ECL": [0.1, 0.2]}
    )
    result = board_pack(aggregate)
    assert result.SEGMENT.isna().sum() == 1
    assert result.loc[result.SEGMENT.isna(), "EAD"].iloc[0] == 1.0


def test_board_pack_is_order_independent():
    aggregate = pd.DataFrame(
        {
            "SEGMENT": ["B", "A", "B"],
            "TOTAL_EAD": [3.0, 2.0, 4.0],
            "TOTAL_ECL": [0.3, 0.2, 0.4],
        }
    )
    pd.testing.assert_frame_equal(
        board_pack(aggregate),
        board_pack(aggregate.sample(frac=1, random_state=7).reset_index(drop=True)),
    )


def test_board_pack_plain_summation():
    aggregate = pd.DataFrame(
        {"SEGMENT": ["A", "A"], "TOTAL_EAD": [2.0, 3.0], "TOTAL_ECL": [0.2, 0.3]}
    )
    pd.testing.assert_frame_equal(
        board_pack(aggregate),
        pd.DataFrame({"SEGMENT": ["A"], "EAD": [5.0], "ECL": [0.5]}),
    )


def test_board_pack_comparison_one_sided_row_fails():
    expected = pd.DataFrame({"SEGMENT": ["A"], "EAD": [10.0], "ECL": [1.0]})
    actual = pd.DataFrame({"SEGMENT": ["B"], "EAD": [10.0], "ECL": [1.0]})
    rows = board_pack_comparison_rows(expected, actual)
    assert all(row["present"] is False for row in rows)
    assert all(row["EAD"]["within_tolerance"] is False for row in rows)


def test_board_pack_comparison_both_missing_is_not_compared():
    expected = pd.DataFrame({"SEGMENT": ["A"], "EAD": [None], "ECL": [None]})
    actual = pd.DataFrame({"SEGMENT": ["A"], "EAD": [None], "ECL": [None]})
    rows = board_pack_comparison_rows(expected, actual)
    assert rows[0]["EAD"]["comparison"] == "not_compared"
    assert rows[0]["ECL"]["comparison"] == "not_compared"
    assert rows[0]["EAD"]["within_tolerance"] is True
    assert rows[0]["ECL"]["within_tolerance"] is True
