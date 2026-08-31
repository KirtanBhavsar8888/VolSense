from __future__ import annotations

from typing import Any

import pandas as pd

from src.calc.iv import compute_iv_delta, validate_iv_delta
from src.calc.parity import synthetic_future
from src.calc.skew import interpolate_25delta_skew, validate_skew


def _summarize_df(df: pd.DataFrame | None) -> dict[str, Any]:
    if df is None or df.empty:
        return {"rows": 0, "columns": [], "summary": {}, "sample": []}

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    summary: dict[str, Any] = {}
    for col in numeric_cols:
        s = df[col].dropna()
        if not s.empty:
            summary[col] = {
                "min": float(s.min()),
                "max": float(s.max()),
                "mean": float(s.mean()),
            }

    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "summary": summary,
        "sample": df.head(3).to_dict(orient="records"),
    }


def _as_tool_result(name: str, payload: Any) -> dict[str, Any]:
    return {"tool": name, "result": payload}


def synthesize_future_tool(session_state: dict[str, Any], risk_free_rate: float = 0.065, outlier_pct: float = 1.0) -> dict[str, Any]:
    chain_df = session_state.get("chain_df")
    if chain_df is None:
        return _as_tool_result("synthesize_future", {"error": "Missing chain_df in session_state."})
    try:
        result = synthetic_future(chain_df, risk_free_rate=risk_free_rate, outlier_pct=outlier_pct)
        session_state["futures_df"] = result
        return _as_tool_result("synthesize_future", _summarize_df(result))
    except Exception as exc:
        return _as_tool_result("synthesize_future", {"error": str(exc)})


def compute_iv_delta_tool(session_state: dict[str, Any], risk_free_rate: float = 0.065) -> dict[str, Any]:
    chain_df = session_state.get("chain_df")
    futures_df = session_state.get("futures_df")
    if chain_df is None:
        return _as_tool_result("compute_iv_delta", {"error": "Missing chain_df in session_state."})
    if futures_df is None:
        return _as_tool_result("compute_iv_delta", {"error": "Missing futures_df in session_state."})
    try:
        result = compute_iv_delta(chain_df, futures_df, risk_free_rate)
        session_state["iv_delta_df"] = result
        return _as_tool_result("compute_iv_delta", _summarize_df(result))
    except Exception as exc:
        return _as_tool_result("compute_iv_delta", {"error": str(exc)})


def validate_iv_delta_tool(session_state: dict[str, Any]) -> dict[str, Any]:
    df = session_state.get("iv_delta_df")
    if df is None:
        return _as_tool_result("validate_iv_delta", {"error": "Missing iv_delta_df in session_state."})
    try:
        result = validate_iv_delta(df)
        return _as_tool_result("validate_iv_delta", result)
    except Exception as exc:
        return _as_tool_result("validate_iv_delta", {"error": str(exc)})


def interpolate_25delta_skew_tool(
    session_state: dict[str, Any],
    target_delta: float = 0.25,
    delta_range: tuple[float, float] = (0.10, 0.50),
) -> dict[str, Any]:
    df = session_state.get("iv_delta_df")
    if df is None:
        return _as_tool_result("interpolate_25delta_skew", {"error": "Missing iv_delta_df in session_state."})
    try:
        result = interpolate_25delta_skew(df, target_delta=target_delta, delta_range=delta_range)
        session_state["skew_df"] = result
        return _as_tool_result("interpolate_25delta_skew", _summarize_df(result))
    except Exception as exc:
        return _as_tool_result("interpolate_25delta_skew", {"error": str(exc)})


def validate_skew_tool(session_state: dict[str, Any], spike_threshold: float = 0.05) -> dict[str, Any]:
    skew_df = session_state.get("skew_df")
    if skew_df is None:
        return _as_tool_result("validate_skew", {"error": "Missing skew_df in session_state."})
    try:
        result = validate_skew(skew_df, spike_threshold=spike_threshold)
        return _as_tool_result("validate_skew", result)
    except Exception as exc:
        return _as_tool_result("validate_skew", {"error": str(exc)})


TOOL_SCHEMAS = [
    {
        "name": "synthesize_future",
        "description": "Build synthetic futures from put-call parity using the current chain_df in the harness session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_free_rate": {"type": "number", "description": "Annualized risk-free rate, e.g. 0.065."},
                "outlier_pct": {"type": "number", "description": "Outlier threshold in percent."},
            },
            "required": [],
        },
    },
    {
        "name": "compute_iv_delta",
        "description": "Compute IV and delta using the current chain_df and futures_df in the harness session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_free_rate": {"type": "number", "description": "Annualized risk-free rate."},
            },
            "required": [],
        },
    },
    {
        "name": "validate_iv_delta",
        "description": "Validate the current iv_delta_df for range and monotonicity checks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "interpolate_25delta_skew",
        "description": "Interpolate 25-delta skew from the current iv_delta_df in the harness session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_delta": {"type": "number", "description": "Target delta, typically 0.25."},
                "delta_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Two-element delta range for interpolation.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "validate_skew",
        "description": "Validate the current skew_df for range and spike behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spike_threshold": {"type": "number", "description": "Threshold for skew change spike detection."},
            },
            "required": [],
        },
    },
]


TOOL_FUNCTIONS = {
    "synthesize_future": synthesize_future_tool,
    "compute_iv_delta": compute_iv_delta_tool,
    "validate_iv_delta": validate_iv_delta_tool,
    "interpolate_25delta_skew": interpolate_25delta_skew_tool,
    "validate_skew": validate_skew_tool,
}


def call_tool(session_state: dict[str, Any], name: str, **kwargs: Any) -> dict[str, Any]:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"tool": name, "result": {"error": f"Unknown tool: {name}"}}
    return fn(session_state, **kwargs)
