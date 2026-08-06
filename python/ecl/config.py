from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "rules"

def table(name: str) -> pd.DataFrame:
    return pd.read_csv(RULES / name, comment="#")

def params() -> dict[str, str]:
    d = table("model_params.csv")
    return dict(zip(d.PARAM, d.VALUE))
