from pathlib import Path
import pandas as pd

def load_period(root: Path, period: str):
    tape = pd.read_csv(root / "data/input" / f"loan_tape_{period}.csv", dtype={"ACCOUNT_ID": "string", "DPD": "string"})
    collateral = pd.read_csv(root / "data/input" / f"collateral_{period}.csv", dtype={"ACCOUNT_ID": "string"})
    scenarios = pd.read_csv(root / "data/input/macro_scenarios.csv")
    return tape, collateral, scenarios

def write_outputs(out: pd.DataFrame, root: Path, period: str):
    path = root / "data/output"
    path.mkdir(parents=True, exist_ok=True)
    export = out.copy()
    export["N_EXPOSURES"] = export["N_EXPOSURES"].astype(int).astype(str)
    for column in ["TOTAL_EAD", "TOTAL_ECL"]:
        export[column] = export[column].map(lambda value: f"{value:.2f}")
    export["COVERAGE"] = export["COVERAGE"].map(
        lambda value: f"{value:.6f}".rstrip("0").rstrip(".")
    )
    export.to_csv(path / f"ecl_by_segment_{period}.csv", index=False)
    with (path / f"ECL_GL_FEED_{period}.txt").open("w") as f:
        for r in out.itertuples(index=False):
            segment = str(r.SEGMENT)[:20].ljust(20)
            f.write(f"{segment}{int(r.STAGE):01d}{r.TOTAL_ECL:18.2f}\n")
