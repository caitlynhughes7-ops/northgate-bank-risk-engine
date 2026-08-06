"""Display formats corresponding to the legacy product SAS formats."""

import math
from numbers import Real

import pandas as pd

from .config import table


_SEGMENT_FORMAT = dict(
    zip(
        table("fmt_seg.csv")["SEGMENT"],
        table("fmt_seg.csv")["LABEL"],
    )
)
_STAGE_FORMAT = dict(
    zip(
        pd.to_numeric(table("fmt_stage.csv")["STAGE"]),
        table("fmt_stage.csv")["LABEL"],
    )
)


def segment_label(code: object) -> str:
    """Render a segment code using the legacy ``$seg.`` format."""
    if code is None or (isinstance(code, float) and math.isnan(code)):
        return _SEGMENT_FORMAT["other"]
    if not isinstance(code, str):
        return _SEGMENT_FORMAT["other"]
    return _SEGMENT_FORMAT.get(code.rstrip(" "), _SEGMENT_FORMAT["other"])


def segment_labels(codes: pd.Series) -> pd.Series:
    """Render a Series of segment codes without mutating the input."""
    return codes.map(segment_label).astype("object")


def _numeric_stage(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Real):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return numeric if math.isfinite(numeric) else None


def _render_numeric(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return format(value, ".15g")


def stage_label(value: object) -> str:
    """Render a stage value using the legacy ``stage.`` format."""
    numeric = _numeric_stage(value)
    if numeric is None:
        return "."
    if numeric in _STAGE_FORMAT:
        return _STAGE_FORMAT[numeric]
    return _render_numeric(numeric)


def stage_labels(values: pd.Series) -> pd.Series:
    """Render a Series of stages without mutating the input."""
    return values.map(stage_label).astype("object")
