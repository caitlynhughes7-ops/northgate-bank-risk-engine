from pathlib import Path
import json
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

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
                    e == a if col == "N_EXPOSURES" else abs(diff) <= 0.01 + 1e-9
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

def compare(period="202409"):
    subprocess.run([sys.executable, "-m", "ecl.cli", "--period", period], cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "python")}, check=True)
    expected = pd.read_csv(ROOT / "data/expected" / f"ecl_by_segment_{period}.csv")
    actual = pd.read_csv(ROOT / "data/output" / f"ecl_by_segment_{period}.csv")
    rows = comparison_rows(expected, actual)
    passed = all(r["present"] and r["N_EXPOSURES"]["within_tolerance"] and r["TOTAL_EAD"]["within_tolerance"] and r["TOTAL_ECL"]["within_tolerance"] for r in rows)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    artifact = {"overall_pass": passed, "tolerance": 0.01, "engine_version": "1.0.0", "engine_commit": commit, "rows": rows}
    (ROOT / "data/output" / f"parity_{period}.json").write_text(json.dumps(artifact, indent=2, allow_nan=False))
    pd.json_normalize(rows).to_csv(ROOT / "data/output" / f"parity_{period}.csv", index=False)
    return passed

if __name__ == "__main__":
    raise SystemExit(0 if compare() else 1)
