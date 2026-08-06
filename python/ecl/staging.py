import pandas as pd
from .config import params, table
from .util_logging import log_step

def stage(d: pd.DataFrame) -> pd.DataFrame:
    log_step("staging_sicr")
    p = params()
    x = d.merge(table("sicr_thresholds.csv"), on="SEGMENT", how="left")
    x["REL_PD_MULT"] = x.REL_PD_MULT.fillna(float(p["sicr_default_rel_pd_mult"]))
    x["ABS_PD_INCR"] = x.ABS_PD_INCR.fillna(float(p["sicr_default_abs_pd_incr"]))
    x["DPD_TRIGGER"] = x.DPD_TRIGGER.fillna(float(p["sicr_default_dpd_trigger"]))
    x["STAGE"] = 1
    x["SICR_REASON"] = "NONE"
    mask = x.DEFAULT_FL | (x.DPD_N >= float(p["staging_default_dpd"]))
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
