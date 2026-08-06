from pathlib import Path
import json

import pandas as pd

from ecl.board_pack import board_pack
from ecl.engine import run


ROOT = Path(__file__).resolve().parents[1]


def _safe(value):
    return None if pd.isna(value) else float(value)


def main() -> None:
    aggregate, account_level = run("202409", ROOT, write=False)
    from_aggregate = board_pack(aggregate).rename(
        columns={"EAD": "aggregate_ead", "ECL": "aggregate_ecl"}
    )
    direct = (
        account_level.groupby("SEGMENT", dropna=False, as_index=False)
        .agg(direct_ead=("EAD", "sum"), direct_ecl=("ECL", "sum"))
    )
    rounded = (
        pd.read_csv(ROOT / "data/expected/ecl_by_segment_202409.csv")
        .groupby("SEGMENT", dropna=False, as_index=False)
        .agg(rounded_ead=("TOTAL_EAD", "sum"), rounded_ecl=("TOTAL_ECL", "sum"))
    )
    merged = from_aggregate.merge(direct, on="SEGMENT", how="outer").merge(
        rounded, on="SEGMENT", how="outer"
    )
    rows = []
    for row in merged.to_dict("records"):
        segment = None if pd.isna(row["SEGMENT"]) else row["SEGMENT"]
        values = {
            key: _safe(row[key])
            for key in [
                "aggregate_ead",
                "aggregate_ecl",
                "direct_ead",
                "direct_ecl",
                "rounded_ead",
                "rounded_ecl",
            ]
        }
        rows.append(
            {
                "SEGMENT": segment,
                **values,
                "aggregate_minus_direct_ead": _safe(
                    row["aggregate_ead"] - row["direct_ead"]
                ),
                "aggregate_minus_direct_ecl": _safe(
                    row["aggregate_ecl"] - row["direct_ecl"]
                ),
                "aggregate_minus_rounded_ead": _safe(
                    row["aggregate_ead"] - row["rounded_ead"]
                ),
                "aggregate_minus_rounded_ecl": _safe(
                    row["aggregate_ecl"] - row["rounded_ecl"]
                ),
                "direct_minus_rounded_ead": _safe(
                    row["direct_ead"] - row["rounded_ead"]
                ),
                "direct_minus_rounded_ecl": _safe(
                    row["direct_ecl"] - row["rounded_ecl"]
                ),
            }
        )
    artifact = {
        "period": "202409",
        "comparison_basis": {
            "aggregate": "board pack built from unrounded segment×stage aggregate",
            "direct": "segment sums computed from account-level EAD and ECL results",
            "rounded": "sums of 2dp ecl_by_segment baseline export rows",
        },
        "rows": rows,
    }
    (ROOT / "data/output/whatif_board_pack_202409.json").write_text(
        json.dumps(artifact, indent=2, allow_nan=False)
    )


if __name__ == "__main__":
    main()
