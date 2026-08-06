import pandas as pd
from .config import params
from .util_logging import log_step

def calculate(exposure: pd.DataFrame, curve: pd.DataFrame) -> pd.DataFrame:
    log_step("ecl_calc")
    horizon = int(float(params()["stage_1_horizon_m"]))
    c = curve.merge(exposure[["ACCOUNT_ID", "STAGE", "LGD", "EAD", "OVERLAY_FACTOR", "SEGMENT"]], on="ACCOUNT_ID", how="inner")
    c = c[(c["STAGE"] != 1) | (c["T"] <= horizon)]
    raw = (c.assign(part=c.PD_MARG * c.LGD * c.EAD * c.DF).groupby("ACCOUNT_ID", as_index=False).part.sum().rename(columns={"part": "ECL_UNADJ"}))
    x = exposure[["ACCOUNT_ID", "SEGMENT", "STAGE", "EAD", "LGD", "OVERLAY_FACTOR"]].merge(raw, on="ACCOUNT_ID", how="left")
    x["ECL"] = x.ECL_UNADJ.fillna(0).mul(x.OVERLAY_FACTOR)
    x.loc[x.STAGE == 3, "ECL"] = x.LGD * x.EAD * x.OVERLAY_FACTOR
    return x
