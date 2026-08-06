import pandas as pd
import pytest

from ecl.config import table
from ecl.formats import (
    grade_label,
    grade_labels,
    segment_label,
    segment_labels,
    stage_label,
    stage_labels,
)


@pytest.mark.parametrize(
    ("code", "label"),
    [
        ("RETAIL_MORTGAGE", "Retail mortgages"),
        ("BTL_MORTGAGE", "Buy to let"),
        ("PERSONAL_LOAN", "Personal loans"),
        ("CREDIT_CARD", "Credit cards"),
        ("OVERDRAFT", "Overdrafts"),
        ("SME_TERM", "SME lending"),
    ],
)
def test_segment_labels_match_legacy_values(code, label):
    assert segment_label(code) == label


def test_segment_other_code_uses_silent_unclassified_catch_all():
    assert segment_label("ASSET_FINANCE") == "Unclassified"


def test_segment_trailing_blanks_match_but_leading_blanks_do_not():
    assert segment_label("RETAIL_MORTGAGE   ") == "Retail mortgages"
    assert segment_label(" RETAIL_MORTGAGE") == "Unclassified"


def test_segment_comparison_is_case_sensitive():
    assert segment_label("retail_mortgage") == "Unclassified"


@pytest.mark.parametrize("value", ["", "   ", None, float("nan")])
def test_segment_blank_or_missing_uses_catch_all(value):
    assert segment_label(value) == "Unclassified"


@pytest.mark.parametrize(
    ("value", "label"),
    [
        (1, "Stage 1 - 12m ECL"),
        (2, "Stage 2 - lifetime ECL"),
        (3, "Stage 3 - credit impaired"),
    ],
)
def test_stage_labels_match_legacy_values(value, label):
    assert stage_label(value) == label


@pytest.mark.parametrize("value", [1.0, "1", "1.0", " 1 "])
def test_stage_lookup_is_numeric_across_input_types(value):
    assert stage_label(value) == "Stage 1 - 12m ECL"


def test_stage_unmatched_numeric_has_no_catch_all_label():
    assert stage_label(4) == "4"
    assert stage_label(4.0) == "4"
    assert stage_label(4.5) == "4.5"
    assert stage_label(-4.5) == "-4.5"


@pytest.mark.parametrize("value", [None, float("nan"), "not-a-stage", ""])
def test_stage_missing_or_non_numeric_uses_sas_missing_rendering(value):
    assert stage_label(value) == "."


def test_series_formats_do_not_mutate_input_and_map_float_promoted_stages():
    segments = pd.Series(["RETAIL_MORTGAGE", "ASSET_FINANCE"], name="SEGMENT")
    stages = pd.Series([1, 2, 4], dtype="float64", name="STAGE")
    original_segments = segments.copy()
    original_stages = stages.copy()

    assert segment_labels(segments).tolist() == ["Retail mortgages", "Unclassified"]
    assert stage_labels(stages).tolist() == [
        "Stage 1 - 12m ECL",
        "Stage 2 - lifetime ECL",
        "4",
    ]
    pd.testing.assert_series_equal(segments, original_segments)
    pd.testing.assert_series_equal(stages, original_stages)


def test_format_config_matches_sas_source_verbatim():
    assert table("fmt_seg.csv").to_dict("records") == [
        {"SEGMENT": "RETAIL_MORTGAGE", "LABEL": "Retail mortgages"},
        {"SEGMENT": "BTL_MORTGAGE", "LABEL": "Buy to let"},
        {"SEGMENT": "PERSONAL_LOAN", "LABEL": "Personal loans"},
        {"SEGMENT": "CREDIT_CARD", "LABEL": "Credit cards"},
        {"SEGMENT": "OVERDRAFT", "LABEL": "Overdrafts"},
        {"SEGMENT": "SME_TERM", "LABEL": "SME lending"},
        {"SEGMENT": "other", "LABEL": "Unclassified"},
    ]
    assert table("fmt_stage.csv").to_dict("records") == [
        {"STAGE": 1, "LABEL": "Stage 1 - 12m ECL"},
        {"STAGE": 2, "LABEL": "Stage 2 - lifetime ECL"},
        {"STAGE": 3, "LABEL": "Stage 3 - credit impaired"},
    ]


@pytest.mark.parametrize(
    ("value", "label"),
    [
        (1, "AAA/AA"),
        (2, "A"),
        (3, "BBB+"),
        (4, "BBB"),
        (5, "BBB-"),
        (6, "BB+"),
        (7, "BB"),
        (8, "BB-"),
        (9, "B+"),
        (10, "B"),
        (11, "B-"),
        (12, "CCC"),
        (13, "CC"),
        (14, "C"),
        (15, "D"),
    ],
)
def test_grade_labels_match_legacy_values(value, label):
    assert grade_label(value) == label


@pytest.mark.parametrize("value", [7, 7.0, "7", "7.0", " 7 "])
def test_grade_lookup_is_numeric_across_input_types(value):
    assert grade_label(value) == "BB"


def test_series_formats_float_promoted_grades():
    grades = pd.Series([7, None], dtype="float64", name="RATING_GRADE")
    original = grades.copy()

    assert grade_labels(grades).tolist() == ["BB", "."]
    assert grade_labels(grades).dtype == "object"
    pd.testing.assert_series_equal(grades, original)


@pytest.mark.parametrize("value", [0, 16, 16.0, 20.5])
def test_grade_unmatched_numeric_has_no_catch_all_label(value):
    assert grade_label(value) == str(value).removesuffix(".0")


@pytest.mark.parametrize("value", [None, float("nan"), "", "not-a-grade"])
def test_grade_missing_or_non_numeric_uses_sas_missing_rendering(value):
    assert grade_label(value) == "."


def test_grade_format_config_matches_sas_source_verbatim():
    assert table("fmt_grade.csv").to_dict("records") == [
        {"RATING_GRADE": 1, "LABEL": "AAA/AA"},
        {"RATING_GRADE": 2, "LABEL": "A"},
        {"RATING_GRADE": 3, "LABEL": "BBB+"},
        {"RATING_GRADE": 4, "LABEL": "BBB"},
        {"RATING_GRADE": 5, "LABEL": "BBB-"},
        {"RATING_GRADE": 6, "LABEL": "BB+"},
        {"RATING_GRADE": 7, "LABEL": "BB"},
        {"RATING_GRADE": 8, "LABEL": "BB-"},
        {"RATING_GRADE": 9, "LABEL": "B+"},
        {"RATING_GRADE": 10, "LABEL": "B"},
        {"RATING_GRADE": 11, "LABEL": "B-"},
        {"RATING_GRADE": 12, "LABEL": "CCC"},
        {"RATING_GRADE": 13, "LABEL": "CC"},
        {"RATING_GRADE": 14, "LABEL": "C"},
        {"RATING_GRADE": 15, "LABEL": "D"},
    ]
