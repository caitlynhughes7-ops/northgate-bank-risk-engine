import pandas as pd

def derive_arrears(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    x["ARREARS_BUCKET"] = "UNK"
    x.loc[x.DPD_N == 0, "ARREARS_BUCKET"] = "0"
    x.loc[x.DPD_N.between(1, 29), "ARREARS_BUCKET"] = "1-29"
    x.loc[x.DPD_N.between(30, 59), "ARREARS_BUCKET"] = "30-59"
    x.loc[x.DPD_N.between(60, 89), "ARREARS_BUCKET"] = "60-89"
    x.loc[x.DPD_N >= 90, "ARREARS_BUCKET"] = "90+"
    adjust = (x.ARREARS_BUCKET == "1-29") & (x.MONTHLY_PAYMENT > 0) & (x.DRAWN_BAL > 0) & ((x.DPD_N * x.MONTHLY_PAYMENT / x.DRAWN_BAL) < 0.001)
    x.loc[adjust, "ARREARS_BUCKET"] = "0"
    return x
