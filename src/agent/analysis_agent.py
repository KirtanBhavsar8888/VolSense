from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
import pandas as pd

from src.agent.tools import TOOL_SCHEMAS, call_tool
from src.verification.bounds_check import flag_bad_chain


DEFAULT_SYSTEM_PROMPT = (
    "You are a disciplined options skew analysis agent. "
    "Use the calc tools to compute synthetic futures, IV/delta, and 25-delta skew. "
    "Do not hallucinate results. Base your answer on actual tool outputs and summarize them clearly."
)


def _compact_chain_summary(chain_df: pd.DataFrame) -> str:
    if chain_df is None:
        return "No chain_df loaded."
    if chain_df.empty:
        return "chain_df is empty."

    timestamp_col = "timestamp" if "timestamp" in chain_df.columns else chain_df.columns[0]
    try:
        start_dt = pd.to_datetime(chain_df[timestamp_col]).min()
        end_dt = pd.to_datetime(chain_df[timestamp_col]).max()
    except Exception:
        start_dt = "n/a"
        end_dt = "n/a"

    sample = chain_df.head(3).to_dict(orient="records")
    return (
        f"rows={len(chain_df)} | "
        f"date_range={start_dt} to {end_dt} | "
        f"columns={list(chain_df.columns)} | "
        f"sample_rows={json.dumps(sample, default=str)}"
    )


def _compact_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    payload = tool_result.get("result", tool_result)
    tool_name = tool_result.get("tool")
    compact: dict[str, Any] = {"tool": tool_name, "error": None}

    if not isinstance(payload, dict):
        compact["summary"] = str(payload)
        return compact

    compact["error"] = payload.get("error")

    has_summary_shape = {"rows", "columns", "summary", "sample"}.issubset(payload.keys())
    if has_summary_shape:
        compact["rows"] = payload.get("rows")
        compact["columns"] = payload.get("columns")
        compact["summary"] = payload.get("summary")
        compact["sample"] = payload.get("sample")
        return compact

    if tool_name in {"validate_iv_delta", "validate_skew"}:
        compact.update(payload)
        return compact

    compact["summary"] = payload
    return compact


def run_analysis_agent(
    chain_df: pd.DataFrame,
    model: str = "openai/gpt-oss-20b",
    max_tool_rounds: int = 6,
    price_ceiling: float | None = None,
    price_scale: float = 10.0,
) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": {"type": "missing_api_key", "message": "GROQ_API_KEY is not set."}}

    sanity = flag_bad_chain(chain_df, price_ceiling=price_ceiling, price_scale=price_scale)
    if sanity["status"] == "fail":
        # Extract the specific issues from the sanity check and build a detailed reason string.
        issues = sanity.get("details", {}).get("issues", [])
        reason = "; ".join(issues) if issues else "chain failed no-arbitrage / edge-case sanity checks"
        return {
            "agent": "analysis_agent",
            "model": model,
            "status": "reroute",
            "reason": reason,
            "sanity": sanity,
            "parameters": {"price_ceiling": price_ceiling, "price_scale": price_scale},
            "session_state": {"chain_df": chain_df, "futures_df": None, "iv_delta_df": None, "skew_df": None},
        }

    session_state: dict[str, Any] = {
        "chain_df": chain_df,
        "futures_df": None,
        "iv_delta_df": None,
        "skew_df": None,
    }

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    
    # Convert tool schemas to OpenAI function format
    openai_tools = []
    for tool in TOOL_SCHEMAS:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        })
    
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze the skew for this option chain. "
                "Use the available calc tools in sequence, beginning with synthetic future generation, "
                "then IV/delta and 25-delta skew. "
                f"Chain summary: {_compact_chain_summary(chain_df)}"
            ),
        }
    ]

    tool_trace: list[dict[str, Any]] = []
    last_response = None

    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            tool_choice="auto" if openai_tools else None,
        )
        last_response = response

        choice = response.choices[0]
        if not choice.message.content and not choice.message.tool_calls:
            return {
                "agent": "analysis_agent",
                "model": model,
                "final_response": "",
                "session_state": session_state,
                "tool_trace": tool_trace,
            }

        # Add assistant message to history
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if choice.message.content:
            assistant_msg["content"] = choice.message.content
        if choice.message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in choice.message.tool_calls
            ]
        messages.append(assistant_msg)

        # If no tool calls, return final response
        if not choice.message.tool_calls:
            return {
                "agent": "analysis_agent",
                "model": model,
                "final_response": choice.message.content or "",
                "session_state": session_state,
                "tool_trace": tool_trace,
            }

        # Execute tool calls
        for tc in choice.message.tool_calls:
            tool_name = tc.function.name
            try:
                import json as json_mod
                tool_args = json_mod.loads(tc.function.arguments)
                tool_result = call_tool(session_state, tool_name, **tool_args)
            except Exception as e:
                tool_result = {
                    "error": str(e),
                    "tool": tool_name,
                }
            
            tool_trace.append({
                "tool": tool_name,
                "input": tool_args if 'tool_args' in dir() else {},
                "output": tool_result,
            })
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(_compact_tool_result(tool_result), default=str),
            })

    return {
        "agent": "analysis_agent",
        "model": model,
        "final_response": "Tool loop reached max rounds without a final non-tool response.",
        "session_state": session_state,
        "tool_trace": tool_trace,
        "last_response": getattr(last_response, "model_dump", lambda: None)(),
    }
