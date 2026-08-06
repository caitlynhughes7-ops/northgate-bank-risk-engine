from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path
import re
from collections.abc import Callable

import pandas as pd

from .config import table
from .util_logging import emit_log_line, log_step


@dataclass(frozen=True)
class ReconControlsResult:
    drawn: float | None
    ead: float | None
    ecl: float | None
    null_stage_count: int


def _params() -> dict[str, str]:
    values = table("recon_controls.csv")
    return dict(zip(values.PARAM, values.VALUE))


def env_recon_tolerance(env: str) -> float:
    root = Path(__file__).resolve().parents[2]
    text = (root / "config" / "env" / f"{env.lower()}.cfg").read_text()
    match = re.search(r"%let\s+RECON_TOL\s*=\s*([^;]+);", text, re.IGNORECASE)
    if match is None:
        raise ValueError(f"RECON_TOL is not defined for environment {env}")
    return float(match.group(1).strip())


def sas_sum(frame: pd.DataFrame, column: str) -> float | None:
    values = frame[column].dropna()
    if values.empty:
        return None
    return float(values.sum())


def numeric_missing(value: object) -> bool:
    return not isinstance(value, str) and bool(pd.isna(value))


def _round_decimal(number: float, decimals: int) -> Decimal:
    exact = Decimal.from_float(number)
    quantum = Decimal(1).scaleb(-decimals)
    with localcontext() as context:
        context.prec = max(
            len(exact.as_tuple().digits),
            exact.adjusted() + 1,
            28,
        ) + decimals + 2
        return exact.quantize(quantum, rounding=ROUND_HALF_UP)


def _significant_digits(candidate: str) -> int:
    mantissa = candidate.upper().split("E", 1)[0].lstrip("+-").replace(".", "")
    significant = mantissa.lstrip("0")
    return len(significant) or 1


def _round_scientific(number: float, decimals: int) -> Decimal:
    exact = Decimal.from_float(number)
    quantum = Decimal(1).scaleb(exact.adjusted() - decimals)
    with localcontext() as context:
        context.prec = max(len(exact.as_tuple().digits), 28) + decimals + 2
        return exact.quantize(quantum, rounding=ROUND_HALF_UP)


def best12(value: float | int | None) -> str:
    """Render a number using the retained-width BEST12. convention."""
    params = _params()
    width = int(params["best12_width"])
    max_decimals = int(params["best12_max_decimals"])
    exponent_decimals = int(params["best12_exponent_decimals"])
    if value is None or bool(pd.isna(value)):
        raw = "."
    else:
        number = float(value)
        fixed_candidate = None
        for decimals in range(max_decimals + 1):
            candidate = f"{number:.{decimals}f}"
            if len(candidate) <= width and float(candidate) == number:
                fixed_candidate = candidate
                break
        if fixed_candidate is None:
            for decimals in range(max_decimals, -1, -1):
                rounded = _round_decimal(number, decimals)
                candidate = format(rounded, "f")
                if len(candidate) <= width and not (number != 0 and float(candidate) == 0):
                    fixed_candidate = (
                        candidate.rstrip("0").rstrip(".")
                        if "." in candidate
                        else candidate
                    )
                    break
        exponent_candidate = None
        for decimals in range(exponent_decimals + 1):
            rounded = _round_scientific(number, decimals)
            candidate = format(rounded, f".{decimals}E")
            if len(candidate) <= width and float(candidate) == number:
                exponent_candidate = candidate
                break
        if exponent_candidate is None:
            for decimals in range(exponent_decimals, -1, -1):
                rounded = _round_scientific(number, decimals)
                candidate = format(rounded, f".{decimals}E")
                if len(candidate) <= width:
                    exponent_candidate = candidate
                    break
        candidates = [
            candidate
            for candidate in (fixed_candidate, exponent_candidate)
            if candidate is not None
        ]
        raw = max(candidates, key=_significant_digits) if candidates else None
    return raw.rjust(width)


def recon_controls(
    tape: pd.DataFrame,
    ecl_acct: pd.DataFrame,
    *,
    now: datetime | None = None,
    emit: Callable[[str], None] | None = None,
) -> ReconControlsResult:
    params = _params()
    log_step("recon_controls", now=now, emit=emit)

    drawn = sas_sum(tape, "DRAWN_BAL")
    ead = sas_sum(ecl_acct, "EAD")
    ecl = sas_sum(ecl_acct, "ECL")
    null_stage_count = sum(numeric_missing(value) for value in ecl_acct["STAGE"])
    logging_params = dict(zip(table("logging.csv").PARAM, table("logging.csv").VALUE))
    formatter = {"best12": best12}[params["control_value_format"]]
    emit_log_line(
        f"{logging_params['log_note_prefix']} {logging_params['log_tag']} "
        f"control drawn={formatter(drawn)} ead={formatter(ead)} ecl={formatter(ecl)}",
        emit,
    )
    if null_stage_count > int(params["null_stage_error_threshold"]):
        error_prefix = logging_params["log_error_prefix"]
        emit_log_line(
            f"{error_prefix} {logging_params['log_tag']} {formatter(null_stage_count)} exposures with null stage",
            emit,
        )
    return ReconControlsResult(
        drawn=drawn,
        ead=ead,
        ecl=ecl,
        null_stage_count=null_stage_count,
    )
