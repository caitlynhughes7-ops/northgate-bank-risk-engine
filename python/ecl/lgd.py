import pandas as pd
from .config import table, params
from .util_logging import log_step

def secured(d: pd.DataFrame, collateral: pd.DataFrame, haircut_overrides: dict[int, float] | None = None) -> pd.DataFrame:
    log_step("lgd_secured")
    x = d[d.SECURED_FLAG == "Y"].copy()
    c = collateral.copy()
    c["ACCOUNT_ID"] = c.ACCOUNT_ID.astype("string").str.replace(r"\s+", "", regex=True)
    x = x.merge(c[["ACCOUNT_ID", "VALUATION", "HPI_INDEX_ORIG", "HPI_INDEX_CURR"]], on="ACCOUNT_ID", how="left")
    h = table("collateral_haircuts.csv")
    x = x.merge(h[["PROD_CD", "HAIRCUT"]], on="PROD_CD", how="left")
    if haircut_overrides:
        for prod_cd, haircut in haircut_overrides.items():
            x.loc[x.PROD_CD == prod_cd, "HAIRCUT"] = haircut
    f = dict(zip(table("lgd_floors.csv").SEGMENT, table("lgd_floors.csv").LGD_FLOOR))
    x["COLL_VALUATION"] = pd.to_numeric(x.VALUATION, errors="coerce").fillna(0)
    orig = pd.to_numeric(x.HPI_INDEX_ORIG, errors="coerce")
    curr = pd.to_numeric(x.HPI_INDEX_CURR, errors="coerce")
    x["HPI_ORIG"] = orig.mask(orig.isna() | (orig == 0), 100)
    x["HPI_CURR"] = curr.mask(curr.isna() | (curr == 0), 100)
    x["HAIRCUT"] = pd.to_numeric(x.HAIRCUT, errors="coerce").fillna(0)
    realisable = x.COLL_VALUATION * (x.HPI_CURR / x.HPI_ORIG) * (1 - x.HAIRCUT)
    x["LGD_RAW"] = ((x.EAD - realisable) / x.EAD).where(x.EAD > 0, 0).clip(lower=0)
    x["LGD"] = x.apply(lambda r: max(r.LGD_RAW, f[r.SEGMENT]) if r.SEGMENT in f else r.LGD_RAW, axis=1)
    return x

def unsecured(d: pd.DataFrame) -> pd.DataFrame:
    log_step("lgd_unsecured")
    x = d[d.SECURED_FLAG != "Y"].copy()
    vals = dict(zip(table("lgd_unsecured.csv").SEGMENT, table("lgd_unsecured.csv").LGD_RAW))
    default = vals["__DEFAULT__"]
    x["LGD_RAW"] = x.SEGMENT.map(vals).fillna(default)
    x["LGD"] = x.LGD_RAW.clip(lower=float(params()["unsecured_lgd_floor"]))
    return x
