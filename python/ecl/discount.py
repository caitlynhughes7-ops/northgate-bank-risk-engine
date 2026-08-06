import pandas as pd
from .util_logging import log_step

def discount(curve: pd.DataFrame) -> pd.DataFrame:
    log_step("discount_eir")
    x = curve.copy()
    x["DF"] = x.apply(lambda r: 1 / (1 + r["EIR"] * r["T"] / 12) if r["SEGMENT"] == "PERSONAL_LOAN" else 1 / ((1 + r["EIR"] / 12) ** r["T"]), axis=1)
    return x
