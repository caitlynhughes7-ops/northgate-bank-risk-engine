import pandas as pd
from .config import table, params

def pd_pit(d: pd.DataFrame, scenarios: pd.DataFrame, weight_file: str | None = None) -> pd.DataFrame:
    p = params()
    wf = weight_file or ("scenario_weights_frozen_v43.csv" if p["active_scenario_weights"] == "frozen_v43" else "scenario_weights.csv")
    weights = table(wf)
    s = scenarios.copy()
    s["SCENARIO"] = s.SCENARIO.astype(str).str.strip().str.upper()
    s = s.merge(weights, on="SCENARIO", how="left").fillna({"WEIGHT": 0})
    scalar = (s.WEIGHT * (1 + float(p["macro_gdp_coefficient"]) * s.GDP_SHOCK + float(p["macro_unemployment_coefficient"]) * (s.UNEMP_RATE - float(p["macro_unemployment_base"])))).sum()
    grades = table("pd_grades.csv")
    gm = dict(zip(grades.RATING_GRADE.astype(str), grades.PD_GRADE))
    x = d.copy()
    x["PD_GRADE"] = x.RATING_GRADE.astype(str).map(gm).fillna(dict(zip(grades.RATING_GRADE.astype(str), grades.PD_GRADE))["__DEFAULT__"])
    x["PD_12M"] = (x.PD_GRADE * scalar).clip(upper=1)
    for bucket, name in [("1-29", "arrears_uplift_1_29"), ("30-59", "arrears_uplift_30_59"), ("60-89", "arrears_uplift_60_89")]:
        x.loc[x.ARREARS_BUCKET == bucket, "PD_12M"] = (x.loc[x.ARREARS_BUCKET == bucket, "PD_12M"] * float(p[name])).clip(upper=1)
    x.loc[x.FORBEARANCE_FL, "PD_12M"] = (x.loc[x.FORBEARANCE_FL, "PD_12M"] * float(p["forbearance_uplift"])).clip(upper=1)
    x.loc[x.DEFAULT_FL, "PD_12M"] = 1
    return x

def term_structure(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cap = int(float(params()["max_term_m"]))
    curves = []
    for row in d.itertuples(index=False):
        h = 1 - (1 - row.PD_12M) ** (1 / 12)
        term = max(1, min(row.REMAIN_TERM_M, cap))
        prev = 0.0
        for t in range(1, int(term) + 1):
            cum = 1 - (1 - h) ** t
            curves.append({"ACCOUNT_ID": row.ACCOUNT_ID, "T": t, "PD_CUM": cum, "PD_MARG": cum - prev, "EIR": row.EIR, "SEGMENT": row.SEGMENT})
            prev = cum
    curve = pd.DataFrame(curves)
    life = curve.groupby("ACCOUNT_ID", as_index=False)["PD_CUM"].max().rename(columns={"PD_CUM": "PD_LIFETIME"})
    return curve, life
