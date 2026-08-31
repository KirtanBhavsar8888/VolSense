"""JSON serialization helpers for pipeline and API persistence."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def _summarize_frame(df: pd.DataFrame) -> dict[str, Any]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    summary: dict[str, Any] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        summary[col] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
        }
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "summary": summary,
        "sample": json_safe(df.head(3).to_dict(orient="records")),
    }


def json_safe(value: Any) -> Any:
    """Convert DataFrames, numpy values, and timestamps into JSON-friendly data."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        return value
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return _summarize_frame(value)
    if isinstance(value, pd.Series):
        return json_safe(value.to_dict())
    if np is not None:
        if isinstance(value, np.generic):
            item = value.item()
            return json_safe(item)
        if isinstance(value, np.ndarray):
            return [json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    try:
        return str(value)
    except Exception:
        return None
