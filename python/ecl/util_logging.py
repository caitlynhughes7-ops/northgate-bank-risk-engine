import sys
from collections.abc import Callable
from datetime import datetime

import pandas as pd

from .config import table

_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


class EclAbort(Exception):
    """Raised when a legacy ECL assertion cancels the run."""


def _logging_params() -> dict[str, str]:
    values = table("logging.csv")
    return dict(zip(values.PARAM, values.VALUE))


def configured_minrows(name: str) -> int:
    values = table("row_count_assertions.csv")
    matches = values.loc[values["DATASET"] == name, "MINROWS"]
    if matches.empty:
        raise KeyError(f"no row-count assertion configured for {name}")
    return int(matches.iloc[0])


def format_datetime20(dt: datetime) -> str:
    return f"{dt.day:02d}{_MONTHS[dt.month - 1]}{dt.year:04d}:{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


_TIMESTAMP_FORMATS = {"datetime20": format_datetime20}


def _write_line(line: str) -> None:
    sys.stdout.write(line + "\n")


def format_log_line(prefix: str, tag: str, body: str) -> str:
    return f"{prefix} {tag} {body}"


def emit_log_line(line: str, emit: Callable[[str], None] | None = None) -> None:
    (emit or _write_line)(line)


def assert_rows(
    frame: pd.DataFrame,
    name: str,
    minrows: int | None = None,
    *,
    emit: Callable[[str], None] | None = None,
) -> None:
    params = _logging_params()
    threshold = int(params["assert_rows_default_minrows"]) if minrows is None else minrows
    n = len(frame.index)
    if n < threshold:
        line = format_log_line(
            params["log_error_prefix"],
            params["log_tag"],
            f"{name} has {n} rows, expected at least {threshold}",
        )
        emit_log_line(line, emit)
        raise EclAbort(line)
    line = format_log_line(params["log_note_prefix"], params["log_tag"], f"{name} row count {n}")
    emit_log_line(line, emit)


def log_step(
    step: str,
    msg: str = "",
    *,
    now: datetime | None = None,
    emit: Callable[[str], None] | None = None,
) -> None:
    params = _logging_params()
    step = str(step).strip()
    msg = str(msg).strip()
    render = _TIMESTAMP_FORMATS[params["log_timestamp_format"]]
    timestamp = render(datetime.now() if now is None else now)
    line = format_log_line(params["log_note_prefix"], params["log_tag"], f"{step} {msg} ({timestamp})")
    emit_log_line(line, emit)
