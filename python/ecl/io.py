from pathlib import Path
import pandas as pd

def load_period(root: Path, period: str):
    tape = pd.read_csv(root / "data/input" / f"loan_tape_{period}.csv", dtype={"ACCOUNT_ID": "string", "DPD": "string"})
    collateral = pd.read_csv(root / "data/input" / f"collateral_{period}.csv", dtype={"ACCOUNT_ID": "string"})
    scenarios = pd.read_csv(root / "data/input/macro_scenarios.csv")
    return tape, collateral, scenarios

def write_outputs(out: pd.DataFrame, root: Path, period: str):
    path = root / "data/output"
    path.mkdir(exist_ok=True)
    out.to_csv(path / f"ecl_by_segment_{period}.csv", index=False, float_format="%.2f")
    with (path / f"ECL_GL_FEED_{period}.txt").open("w") as f:
        for r in out.itertuples(index=False):
            segment = str(r.SEGMENT)[:20].ljust(20)
            f.write(f"{segment}{int(r.STAGE):01d}{r.TOTAL_ECL:18.2f}\n")
