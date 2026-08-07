import pandas as pd

def aggregate(d: pd.DataFrame) -> pd.DataFrame:
    x = d.groupby(["SEGMENT", "STAGE"], dropna=False, as_index=False).agg(N_EXPOSURES=("ACCOUNT_ID", "size"), TOTAL_EAD=("EAD", "sum"), TOTAL_ECL=("ECL", "sum"))
    x["COVERAGE"] = x.TOTAL_ECL.div(x.TOTAL_EAD).where(x.TOTAL_EAD > 0, 0)
    return x.sort_values(["SEGMENT", "STAGE"], na_position="first").reset_index(drop=True)
