from datetime import datetime
from typing import Any

import pandas as pd

from .config import table
from .recon import (
    best12,
    env_recon_tolerance,
    numeric_missing,
    sas_sum,
)
from .util_logging import emit_log_line, log_step


def _rules() -> dict[str, str]:
    values = table("recon_controls.csv")
    return dict(zip(values.PARAM, values.VALUE))


def _logging() -> dict[str, str]:
    values = table("logging.csv")
    return dict(zip(values.PARAM, values.VALUE))


def _safe_tolerance(env: str) -> float | None:
    try:
        return env_recon_tolerance(env)
    except (FileNotFoundError, ValueError):
        return None


def _verdict(relative_difference: float | None, tolerance: float | None) -> bool | None:
    if relative_difference is None or tolerance is None:
        return None
    return relative_difference > tolerance


def recon_observability(
    tape: pd.DataFrame,
    ecl_acct: pd.DataFrame,
    *,
    env: str | None = None,
    now: datetime | None = None,
    emit=None,
) -> dict[str, Any]:
    rules = _rules()
    logging = _logging()
    selected_env = env or rules["default_env"]
    drawn = sas_sum(tape, "DRAWN_BAL")
    ead = sas_sum(ecl_acct, "EAD")
    absolute_difference = None if drawn is None or ead is None else abs(drawn - ead)
    relative_difference = (
        None if absolute_difference is None or drawn == 0 else absolute_difference / abs(drawn)
    )
    env_tolerance = _safe_tolerance(selected_env)
    spec_tolerance = float(rules["spec_section_8_tolerance"])
    null_stage_count = sum(numeric_missing(value) for value in ecl_acct["STAGE"])
    control_1 = {
        "sum_drawn_bal": drawn,
        "sum_ead": ead,
        "absolute_difference": absolute_difference,
        "relative_difference": relative_difference,
        "env": selected_env,
        "env_tolerance": env_tolerance,
        "env_tolerance_breach": _verdict(relative_difference, env_tolerance),
        "spec_section_8_tolerance": spec_tolerance,
        "spec_section_8_tolerance_breach": _verdict(relative_difference, spec_tolerance),
    }
    control_2 = {
        "null_stage_count": null_stage_count,
        "breach": null_stage_count > int(rules["null_stage_error_threshold"]),
    }
    control_3 = {
        "status": "not_evaluable",
        "reason": "No prior-period artifact exists in the repository.",
    }
    artifact = {
        "control_1": control_1,
        "control_2": control_2,
        "control_3": control_3,
        "basis": {
            "legacy_pairing_open_question": (
                "DRAWN_BAL is compared with EAD, although EAD includes "
                "CCF x UNDRAWN by construction under spec section 5; "
                "the appropriate comparison basis is OPEN QUESTION."
            ),
            "decision": "Observability only; no verdict is applied to the run.",
        },
    }
    log_step("recon_observability", now=now, emit=emit)
    prefix = logging["log_observability_prefix"]
    tag = logging["log_tag"]
    emit_log_line(
        f"{prefix} {tag} control1 drawn={best12(drawn)} ead={best12(ead)} "
        f"absolute_difference={absolute_difference} relative_difference={relative_difference} "
        f"env_tolerance_breach={control_1['env_tolerance_breach']} "
        f"spec_tolerance_breach={control_1['spec_section_8_tolerance_breach']}",
        emit,
    )
    emit_log_line(
        f"{prefix} {tag} control2 null_stage_count={best12(null_stage_count)} "
        f"breach={control_2['breach']}",
        emit,
    )
    emit_log_line(f"{prefix} {tag} control3 status=not_evaluable", emit)
    return artifact
