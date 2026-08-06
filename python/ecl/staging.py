import pandas as pd
from .config import table

def stage(d: pd.DataFrame) -> pd.DataFrame:
    x = d.merge(table("sicr_thresholds.csv"), on="SEGMENT", how="left")
    x["REL_PD_MULT"] = x.REL_PD_MULT.fillna(2.0)
    x["ABS_PD_INCR"] = x.ABS_PD_INCR.fillna(0.01)
    x["DPD_TRIGGER"] = x.DPD_TRIGGER.fillna(30)
    x["STAGE"] = 1
    x["SICR_REASON"] = "NONE"
    mask = x.DEFAULT_FL | (x.DPD_N >= 90)
    x.loc[mask, ["STAGE", "SICR_REASON"]] = [3, "IMPAIRED"]
    mask = (x.STAGE == 1) & (x.DPD_N >= x.DPD_TRIGGER)
    x.loc[mask, ["STAGE", "SICR_REASON"]] = [2, "DPD"]
    mask = (x.STAGE == 1) & x.FORBEARANCE_FL
    x.loc[mask, ["STAGE", "SICR_REASON"]] = [2, "FORBEARANCE"]
    mask = (x.STAGE == 1) & x.WATCHLIST_FL
    x.loc[mask, ["STAGE", "SICR_REASON"]] = [2, "WATCHLIST"]
    mask = (x.STAGE == 1) & (x.PD_LIFETIME > x.REL_PD_MULT * x.PD_LIFETIME_ORIG) & ((x.PD_LIFETIME - x.PD_LIFETIME_ORIG) > x.ABS_PD_INCR)
    x.loc[mask, ["STAGE", "SICR_REASON"]] = [2, "QUANT_PD"]
    return x
