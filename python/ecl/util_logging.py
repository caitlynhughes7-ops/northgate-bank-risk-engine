import sys
from collections.abc import Callable
from datetime import datetime

from .config import table

_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def _logging_params() -> dict[str, str]:
    values = table("logging.csv")
    return dict(zip(values.PARAM, values.VALUE))


def format_datetime20(dt: datetime) -> str:
    return f"{dt.day:02d}{_MONTHS[dt.month - 1]}{dt.year:04d}:{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


_TIMESTAMP_FORMATS = {"datetime20": format_datetime20}


def _write_line(line: str) -> None:
    sys.stdout.write(line + "\n")


def format_log_line(prefix: str, tag: str, body: str) -> str:
    return f"{prefix} {tag} {body}"


def emit_log_line(line: str, emit: Callable[[str], None] | None = None) -> None:
    (emit or _write_line)(line)


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
