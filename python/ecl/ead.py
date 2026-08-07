import pandas as pd
from .config import table

def ead_ccf(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    c = table("ccf.csv")
    factors = dict(zip(c.SEGMENT, c.CCF))
    x["CCF"] = x["SEGMENT"].map(factors).fillna(factors["__DEFAULT__"])
    x["EAD"] = (x.DRAWN_BAL + x.CCF * x.UNDRAWN).clip(lower=0)
    return x
