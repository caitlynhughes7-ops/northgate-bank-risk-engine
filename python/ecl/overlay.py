from .config import table
from .util_logging import log_step
import pandas as pd

def apply_overlay(d: pd.DataFrame) -> pd.DataFrame:
    log_step("fli_overlay")
    x = d.copy()
    vals = dict(zip(table("overlay_factors.csv").SEGMENT, table("overlay_factors.csv").OVERLAY_FACTOR))
    x["OVERLAY_FACTOR"] = x.SEGMENT.map(vals).fillna(vals["__DEFAULT__"])
    return x
