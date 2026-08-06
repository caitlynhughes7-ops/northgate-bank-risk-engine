from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from .config import table


class UnsupportedPeriodError(ValueError):
    """Raised when SAS period-date behavior is not verified for an input."""


@dataclass(frozen=True)
class PeriodDates:
    RPT_DT: str
    RPT_DT_SAS: date
    RPT_DT_SAS_SERIAL: int
    PRIOR_YYYYMM: str


def _rules() -> dict[str, str]:
    rules = table("period_dates.csv")
    return dict(zip(rules.PARAM, rules.VALUE))


def _unsupported(yyyymm: str) -> UnsupportedPeriodError:
    return UnsupportedPeriodError(
        f"Legacy period_dates behavior is unverified for {yyyymm!r}; "
        "see docs/migration/PARITY_FINDINGS.md"
    )


def period_dates(yyyymm: str) -> PeriodDates:
    rules = _rules()
    raw = yyyymm.strip()
    if rules["month_alignment"] != "e" or rules["prior_period_format"] != "yymmn6":
        raise RuntimeError("Unsupported period_dates configuration")
    prior_offset = int(rules["prior_month_offset"])
    year_start = int(rules["period_year_start"]) - 1
    month_start = int(rules["period_month_start"]) - 1
    if len(raw) < max(
        year_start + int(rules["period_year_length"]),
        month_start + int(rules["period_month_length"]),
    ):
        raise _unsupported(yyyymm)

    year_text = raw[year_start : year_start + int(rules["period_year_length"])]
    month_text = raw[month_start : month_start + int(rules["period_month_length"])]
    try:
        year = int(year_text)
        month = int(month_text)
        if not 1 <= month <= 12:
            raise ValueError
        reporting = date(year, month, monthrange(year, month)[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise _unsupported(yyyymm) from exc

    epoch = date.fromisoformat(rules["sas_epoch"])
    serial = (reporting - epoch).days
    prior_month = month + prior_offset
    prior_year = year
    while prior_month < 1:
        prior_month += 12
        prior_year -= 1
    while prior_month > 12:
        prior_month -= 12
        prior_year += 1
    prior = f"{prior_year:04d}{prior_month:02d}"
    return PeriodDates(raw, reporting, serial, prior)
