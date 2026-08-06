from pathlib import Path
import json
import subprocess
from itertools import zip_longest
import pandas as pd

from ecl import __version__
from ecl.board_pack import board_pack
from ecl.engine import run

ROOT = Path(__file__).resolve().parents[1]

def engine_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None

def comparison_rows(expected, actual):
    keys = ["SEGMENT", "STAGE"]
    merged = expected.merge(actual, on=keys, how="outer", suffixes=("_EXPECTED", "_ACTUAL"), indicator=True)
    rows = []
    for r in merged.to_dict("records"):
        segment = None if pd.isna(r["SEGMENT"]) else r["SEGMENT"]
        stage = None if pd.isna(r["STAGE"]) else r["STAGE"]
        row = {"SEGMENT": segment, "STAGE": stage, "present": r["_merge"] == "both"}
        for col in ["N_EXPOSURES", "TOTAL_EAD", "TOTAL_ECL", "COVERAGE"]:
            e, a = r.get(col + "_EXPECTED"), r.get(col + "_ACTUAL")
            missing = pd.isna(e) or pd.isna(a)
            e = None if pd.isna(e) else e
            a = None if pd.isna(a) else a
            diff = None if missing else float(a - e)
            verdict = None if col == "COVERAGE" else (
                False if missing else (
                    e == a if col == "N_EXPOSURES" else abs(diff) <= 0.01
                )
            )
            row[col] = {
                "expected": e,
                "actual": a,
                "diff": diff,
                "within_tolerance": verdict,
                "comparison": "not_compared" if col == "COVERAGE" else "compared",
            }
        rows.append(row)
    return rows


def board_pack_comparison_rows(expected, actual, baseline_row_counts=None):
    baseline_row_counts = baseline_row_counts or {}
    merged = expected.merge(
        actual,
        on=["SEGMENT"],
        how="outer",
        suffixes=("_EXPECTED", "_ACTUAL"),
        indicator=True,
    )
    rows = []
    for r in merged.to_dict("records"):
        segment = None if pd.isna(r["SEGMENT"]) else r["SEGMENT"]
        expected_count = baseline_row_counts.get(segment, 0)
        row = {
            "SEGMENT": segment,
            "present": r["_merge"] == "both",
            "baseline_rounding_bound": 0.005 * expected_count,
        }
        for col in ["EAD", "ECL"]:
            e, a = r.get(col + "_EXPECTED"), r.get(col + "_ACTUAL")
            e_missing, a_missing = pd.isna(e), pd.isna(a)
            e = None if e_missing else float(e)
            a = None if a_missing else float(a)
            diff = None if e_missing or a_missing else float(a - e)
            row[col] = {
                "expected": e,
                "actual": a,
                "diff": diff,
                "comparison": (
                    "compared" if not e_missing and not a_missing else "not_compared"
                ),
                "within_tolerance": (
                    True
                    if e_missing and a_missing
                    else False
                    if e_missing or a_missing or r["_merge"] != "both"
                    else abs(diff) <= 0.01
                ),
            }
        rows.append(row)
    return rows

def compare(period="202409"):
    actual, _ = run(period, ROOT)
    expected = pd.read_csv(ROOT / "data/expected" / f"ecl_by_segment_{period}.csv")
    rows = comparison_rows(expected, actual)
    passed = all(r["present"] and r["N_EXPOSURES"]["within_tolerance"] and r["TOTAL_EAD"]["within_tolerance"] and r["TOTAL_ECL"]["within_tolerance"] for r in rows)
    rendered_expected = (ROOT / "data/expected" / f"ecl_by_segment_{period}.csv").read_text().splitlines()
    rendered_actual = (ROOT / "data/output" / f"ecl_by_segment_{period}.csv").read_text().splitlines()
    textual_differences = [
        {"line": index, "expected": expected_line, "actual": actual_line}
        for index, (expected_line, actual_line) in enumerate(
            zip_longest(rendered_expected, rendered_actual), start=1
        )
        if expected_line != actual_line
    ]
    compared_diffs = [
        abs(row[field]["diff"])
        for row in rows
        for field in ["TOTAL_EAD", "TOTAL_ECL"]
        if row[field]["diff"] is not None
    ]
    worst_case_abs_diff = max(compared_diffs, default=0.0)
    commit = engine_commit()
    artifact = {
        "overall_pass": passed,
        "tolerance": 0.01,
        "comparison_basis": "unrounded engine aggregate values versus 2dp SAS baseline export",
        "worst_case_abs_diff": worst_case_abs_diff,
        "engine_version": __version__,
        "engine_commit": commit,
        "rendered_csv_check": {
            "comparison": "informational",
            "match": not textual_differences,
            "differences": textual_differences,
        },
        "rows": rows,
    }
    (ROOT / "data/output" / f"parity_{period}.json").write_text(json.dumps(artifact, indent=2, allow_nan=False))
    pd.json_normalize(rows).to_csv(ROOT / "data/output" / f"parity_{period}.csv", index=False)
    expected_board = (
        expected.groupby("SEGMENT", dropna=False, as_index=False)
        .agg(EAD=("TOTAL_EAD", "sum"), ECL=("TOTAL_ECL", "sum"))
    )
    actual_board = board_pack(actual)
    baseline_row_counts = {
        (None if pd.isna(segment) else segment): int(count)
        for segment, count in expected.groupby("SEGMENT", dropna=False).size().items()
    }
    board_rows = board_pack_comparison_rows(
        expected_board, actual_board, baseline_row_counts
    )
    board_diffs = [
        abs(row[field]["diff"])
        for row in board_rows
        for field in ["EAD", "ECL"]
        if row[field]["diff"] is not None
    ]
    board_worst_case = max(board_diffs, default=0.0)
    max_rounding_bound = max(
        (row["baseline_rounding_bound"] for row in board_rows), default=0.0
    )
    board_passed = all(
        row["present"]
        and row["EAD"]["within_tolerance"]
        and row["ECL"]["within_tolerance"]
        for row in board_rows
    )
    board_artifact = {
        "overall_pass": board_passed,
        "tolerance": 0.01,
        "comparison_basis": "unrounded board-pack values versus sums of 2dp baseline segment×stage export rows",
        "worst_case_abs_diff": board_worst_case,
        "max_baseline_rounding_bound": max_rounding_bound,
        "worst_case_within_baseline_rounding_bound": board_worst_case
        <= max_rounding_bound,
        "engine_version": __version__,
        "engine_commit": commit,
        "rows": board_rows,
    }
    (ROOT / "data/output" / f"parity_board_pack_{period}.json").write_text(
        json.dumps(board_artifact, indent=2, allow_nan=False)
    )
    pd.json_normalize(board_rows).to_csv(
        ROOT / "data/output" / f"parity_board_pack_{period}.csv", index=False
    )
    return passed and board_passed

if __name__ == "__main__":
    raise SystemExit(0 if compare() else 1)
