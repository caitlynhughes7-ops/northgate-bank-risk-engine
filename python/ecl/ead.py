import pandas as pd
from .config import table
from .util_logging import log_step

def ead_ccf(d: pd.DataFrame) -> pd.DataFrame:
    log_step("ead_ccf")
    x = d.copy()
    c = table("ccf.csv")
    factors = dict(zip(c.SEGMENT, c.CCF))
    x["CCF"] = x["SEGMENT"].map(factors).fillna(factors["__DEFAULT__"])
    x["EAD"] = (x.DRAWN_BAL + x.CCF * x.UNDRAWN).clip(lower=0)
    return x
