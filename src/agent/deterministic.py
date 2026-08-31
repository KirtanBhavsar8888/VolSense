"""Deterministic calc-layer analysis that does not require an LLM key."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.agent.tools import call_tool
from src.verification.bounds_check import flag_bad_chain

TOOL_SEQUENCE = [
    "synthesize_future",
    "compute_iv_delta",
    "validate_iv_delta",
    "interpolate_25delta_skew",
    "validate_skew",
]


def _close_skew(skew_df: pd.DataFrame | None) -> float | None:
    if skew_df is None or skew_df.empty or "skew_25d" not in skew_df.columns:
        return None
    valid = skew_df[skew_df["skew_25d"].notna()]
    if valid.empty:
        return None
    return float(valid.iloc[-1]["skew_25d"])


def run_deterministic_analysis(
    chain_df: pd.DataFrame,
    price_ceiling: float | None = None,
    price_scale: float = 10.0,
) -> dict[str, Any]:
    """Run the calc tools in order and return the same shape as the LLM agent."""
    sanity = flag_bad_chain(chain_df, price_ceiling=price_ceiling, price_scale=price_scale)
    if sanity["status"] == "fail":
        issues = sanity.get("details", {}).get("issues", [])
        reason = "; ".join(issues) if issues else "chain failed no-arbitrage / edge-case sanity checks"
        return {
            "agent": "deterministic",
            "model": "calc-layer",
            "status": "reroute",
            "reason": reason,
            "sanity": sanity,
            "final_response": "",
            "session_state": {
                "chain_df": chain_df,
                "futures_df": None,
                "iv_delta_df": None,
                "skew_df": None,
            },
            "tool_trace": [],
        }

    session_state: dict[str, Any] = {
        "chain_df": chain_df,
        "futures_df": None,
        "iv_delta_df": None,
        "skew_df": None,
    }
    tool_trace: list[dict[str, Any]] = []
    for name in TOOL_SEQUENCE:
        output = call_tool(session_state, name)
        tool_trace.append({"tool": name, "input": {}, "output": output})

    close = _close_skew(session_state.get("skew_df"))
    close_text = f"{close:.4f}" if close is not None else "n/a"
    return {
        "agent": "deterministic",
        "model": "calc-layer",
        "status": "completed",
        "final_response": (
            f"Deterministic 25-delta skew analysis completed. "
            f"Close skew_25d (PE IV − CE IV) is {close_text}."
        ),
        "close_skew": close,
        "session_state": session_state,
        "tool_trace": tool_trace,
        "sanity": sanity,
    }
