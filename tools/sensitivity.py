from pathlib import Path
import json

import pandas as pd

from ecl.config import table
from ecl.engine import run

ROOT = Path(__file__).resolve().parents[1]


def _deltas(baseline, variant):
    merged = baseline.merge(
        variant,
        on=["SEGMENT", "STAGE"],
        suffixes=("_BASELINE", "_VARIANT"),
        how="outer",
    )
    merged["TOTAL_ECL_DELTA"] = (
        merged["TOTAL_ECL_VARIANT"] - merged["TOTAL_ECL_BASELINE"]
    ).fillna(merged["TOTAL_ECL_VARIANT"]).fillna(-merged["TOTAL_ECL_BASELINE"])
    rows = []
    for row in merged.to_dict("records"):
        baseline_total = None if merged_value_missing(row["TOTAL_ECL_BASELINE"]) else row["TOTAL_ECL_BASELINE"]
        variant_total = None if merged_value_missing(row["TOTAL_ECL_VARIANT"]) else row["TOTAL_ECL_VARIANT"]
        rows.append(
            {
                "SEGMENT": None if pd.isna(row["SEGMENT"]) else row["SEGMENT"],
                "STAGE": None if pd.isna(row["STAGE"]) else row["STAGE"],
                "baseline_total_ecl": baseline_total,
                "variant_total_ecl": variant_total,
                "delta_total_ecl": None if merged_value_missing(row["TOTAL_ECL_DELTA"]) else row["TOTAL_ECL_DELTA"],
            }
        )
    return rows, float(merged["TOTAL_ECL_DELTA"].sum())


def merged_value_missing(value):
    return value is None or bool(pd.isna(value))


def main() -> None:
    baseline, _ = run("202409", ROOT, write=False)
    configured, _ = run(
        "202409", ROOT, weight_file="scenario_weights.csv", write=False
    )
    haircut_row = table("collateral_haircuts.csv").loc[
        lambda frame: frame["PROD_CD"] == 110
    ].iloc[0]
    btl_fixed, _ = run(
        "202409",
        ROOT,
        haircut_overrides={2110: float(haircut_row["HAIRCUT"])},
        write=False,
    )
    configured_rows, configured_total = _deltas(baseline, configured)
    btl_rows, btl_total = _deltas(baseline, btl_fixed)
    artifact = {
        "period": "202409",
        "baseline": "frozen_v43_legacy",
        "scenarios": {
            "configured_weights": {
                "rows": configured_rows,
                "total_delta_total_ecl": configured_total,
            },
            "btl_prod_2110_haircut_from_prod_110": {
                "rows": btl_rows,
                "total_delta_total_ecl": btl_total,
            },
        },
    }
    (ROOT / "data/output/sensitivity_202409.json").write_text(
        json.dumps(artifact, indent=2, allow_nan=False)
    )


if __name__ == "__main__":
    main()
