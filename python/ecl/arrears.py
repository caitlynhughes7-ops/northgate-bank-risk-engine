import pandas as pd
from .config import params
from .util_logging import log_step

def derive_arrears(d: pd.DataFrame) -> pd.DataFrame:
    log_step("derive_arrears")
    p = params()
    threshold = float(p["arrears_part_month_threshold"])
    x = d.copy()
    x["ARREARS_BUCKET"] = "UNK"
    x.loc[x.DPD_N == 0, "ARREARS_BUCKET"] = "0"
    x.loc[x.DPD_N.between(float(p["arrears_bucket_1_29_min"]), float(p["arrears_bucket_1_29_max"])), "ARREARS_BUCKET"] = "1-29"
    x.loc[x.DPD_N.between(float(p["arrears_bucket_30_59_min"]), float(p["arrears_bucket_30_59_max"])), "ARREARS_BUCKET"] = "30-59"
    x.loc[x.DPD_N.between(float(p["arrears_bucket_60_89_min"]), float(p["arrears_bucket_60_89_max"])), "ARREARS_BUCKET"] = "60-89"
    x.loc[x.DPD_N >= float(p["arrears_bucket_90_plus_min"]), "ARREARS_BUCKET"] = "90+"
    adjust = (x.ARREARS_BUCKET == "1-29") & (x.MONTHLY_PAYMENT > 0) & (x.DRAWN_BAL > 0) & ((x.DPD_N * x.MONTHLY_PAYMENT / x.DRAWN_BAL) < threshold)
    x.loc[adjust, "ARREARS_BUCKET"] = "0"
    return x
