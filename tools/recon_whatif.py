import json
from pathlib import Path

from ecl.arrears import derive_arrears
from ecl.clean import clean
from ecl.engine import run
from ecl.io import load_period
from ecl.product import map_products
from ecl.recon import env_recon_tolerance
from ecl.config import table


ROOT = Path(__file__).resolve().parents[1]
PERIOD = "202409"


def _sum(frame, column):
    values = frame[column].dropna()
    return None if values.empty else float(values.sum())


def evaluate_tolerances(drawn, ead, tolerances):
    if drawn is None or ead is None or drawn == 0:
        return {
            name: {
                "tolerance": tolerance,
                "pass": None,
                "currency_excess": None,
                "currency_headroom": None,
            }
            for name, tolerance in tolerances.items()
        }
    absolute_difference = abs(drawn - ead)
    relative_difference = absolute_difference / abs(drawn)
    return {
        name: {
            "tolerance": tolerance,
            "pass": relative_difference <= tolerance,
            "currency_excess": max(absolute_difference - abs(drawn) * tolerance, 0.0),
            "currency_headroom": max(abs(drawn) * tolerance - absolute_difference, 0.0),
        }
        for name, tolerance in tolerances.items()
    }


def main() -> None:
    tape, _, _ = load_period(ROOT, PERIOD)
    arrears = derive_arrears(map_products(clean(tape)))
    _, account = run(PERIOD, ROOT, write=False)
    drawn = _sum(arrears, "DRAWN_BAL")
    ead = _sum(account, "EAD")
    absolute_difference = None if drawn is None or ead is None else abs(drawn - ead)
    relative_difference = (
        None
        if absolute_difference is None or drawn == 0
        else absolute_difference / abs(drawn)
    )
    tolerances = {
        "prod_recon_tol": env_recon_tolerance("prod"),
        "uat_recon_tol": env_recon_tolerance("uat"),
        "spec_section_8": float(
            dict(zip(table("recon_controls.csv").PARAM, table("recon_controls.csv").VALUE))[
                "spec_section_8_tolerance"
            ]
        ),
    }
    tolerance_results = evaluate_tolerances(drawn, ead, tolerances)
    rows = (
        account.groupby(["SEGMENT", "STAGE"], dropna=False, as_index=False)
        .agg(total_ead=("EAD", "sum"), total_ecl=("ECL", "sum"))
        .sort_values(["SEGMENT", "STAGE"], na_position="first")
    )
    withheld = [
        {
            "segment": None if row.SEGMENT != row.SEGMENT else row.SEGMENT,
            "stage": None if row.STAGE != row.STAGE else int(row.STAGE),
            "total_ead": float(row.total_ead),
            "total_ecl": float(row.total_ecl),
        }
        for row in rows.itertuples(index=False)
    ]
    artifact = {
        "period": PERIOD,
        "basis": {
            "legacy_pairing_open_question": (
                "DRAWN_BAL is compared with EAD, although EAD includes "
                "CCF x UNDRAWN by construction under spec section 5; "
                "the appropriate corrected comparison basis is OPEN QUESTION."
            ),
            "relative_difference_denominator": "sum(DRAWN_BAL)",
        },
        "control_1": {
            "sum_drawn_bal": drawn,
            "sum_ead": ead,
            "absolute_difference": absolute_difference,
            "relative_difference": relative_difference,
            "candidate_tolerances": tolerance_results,
        },
        "control_2": {
            "null_stage_count": int(account["STAGE"].isna().sum()),
            "expected": 0,
            "impact": "none",
        },
        "control_3": {
            "status": "not_evaluable",
            "reason": "No prior-period artifact exists in the repository.",
        },
        "corrected_ordering_withheld_publication": {
            "description": (
                "If a failing corrected control blocked publication, these "
                "SEGMENT x STAGE amounts would be withheld from disclosure and GL."
            ),
            "rows": withheld,
            "total_ead": float(rows["total_ead"].sum()),
            "total_ecl": float(rows["total_ecl"].sum()),
        },
    }
    output = ROOT / "data/output/whatif/recon_controls_202409.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
