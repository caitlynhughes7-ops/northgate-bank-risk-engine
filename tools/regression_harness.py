from pathlib import Path
import json
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def compare(period="202409"):
    subprocess.run([sys.executable, "-m", "ecl.cli", "--period", period], cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "python")}, check=True)
    expected = pd.read_csv(ROOT / "data/expected" / f"ecl_by_segment_{period}.csv")
    actual = pd.read_csv(ROOT / "data/output" / f"ecl_by_segment_{period}.csv")
    keys = ["SEGMENT", "STAGE"]
    merged = expected.merge(actual, on=keys, how="outer", suffixes=("_EXPECTED", "_ACTUAL"), indicator=True)
    rows = []
    for r in merged.to_dict("records"):
        row = {"SEGMENT": r["SEGMENT"], "STAGE": r["STAGE"], "present": r["_merge"] == "both"}
        for col in ["N_EXPOSURES", "TOTAL_EAD", "TOTAL_ECL", "COVERAGE"]:
            e, a = r.get(col + "_EXPECTED"), r.get(col + "_ACTUAL")
            diff = None if pd.isna(e) or pd.isna(a) else float(a - e)
            row[col] = {"expected": e, "actual": a, "diff": diff, "within_tolerance": (False if col == "N_EXPOSURES" and e != a else True if col == "COVERAGE" or pd.isna(e) or pd.isna(a) else abs(diff) <= 0.01 + 1e-9)}
        rows.append(row)
    passed = all(r["present"] and r["N_EXPOSURES"]["within_tolerance"] and r["TOTAL_EAD"]["within_tolerance"] and r["TOTAL_ECL"]["within_tolerance"] for r in rows)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    artifact = {"overall_pass": passed, "tolerance": 0.01, "engine_version": "1.0.0", "engine_commit": commit, "rows": rows}
    (ROOT / "data/output/parity_202409.json").write_text(json.dumps(artifact, indent=2, default=lambda x: None if pd.isna(x) else x))
    pd.json_normalize(rows).to_csv(ROOT / "data/output/parity_202409.csv", index=False)
    return passed

if __name__ == "__main__":
    raise SystemExit(0 if compare() else 1)
