import pandas as pd
from .util_logging import assert_rows, configured_minrows, log_step

def clean(tape: pd.DataFrame) -> pd.DataFrame:
    log_step("clean_loan_tape")
    d = tape.copy()
    d["ACCOUNT_ID"] = d["ACCOUNT_ID"].astype("string").str.replace(r"\s+", "", regex=True)
    d["DRAWN_BAL"] = d["DRAWN_BAL"].fillna(0)
    d["UNDRAWN"] = d["UNDRAWN"].fillna(0)
    raw = d["DPD"].astype("string").str.strip()
    d["DPD_N"] = pd.to_numeric(raw.replace({"N/A": "0", "": "0", ".": "0", "NULL": "0"}), errors="coerce").fillna(0)
    d.loc[d["DPD_N"] == 999, "DPD_N"] = 0
    for source, target in [("FORBEARANCE", "FORBEARANCE_FL"), ("WATCHLIST", "WATCHLIST_FL"), ("DEFAULT_IND", "DEFAULT_FL")]:
        d[target] = d[source].astype("string").str.upper().isin(["Y", "YES", "1"])
    d.loc[d["IO_FLAG"].astype("string").str.strip() == "Y", "MONTHLY_PAYMENT"] = 0
    d.loc[d["EIR"] > 1, "EIR"] = d.loc[d["EIR"] > 1, "EIR"] / 100
    cleaned = d.drop(columns=["DPD", "FORBEARANCE", "WATCHLIST", "DEFAULT_IND"])
    assert_rows(cleaned, "stg.tape_clean", configured_minrows("stg.tape_clean"))
    return cleaned
