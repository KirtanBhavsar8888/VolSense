from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai import APITimeoutError, RateLimitError, APIStatusError


DEFAULT_PROMPT = (
    "You are an options analyst. "
    "Analyze the skew in the provided Nifty option chain CSV and give a concise trading interpretation. "
    "Focus on the option skew shape, relative IV levels, whether the market is pricing fear or complacency, "
    "and any likely directional or mean-reversion signals. "
    "Do not use tools or external data; base your answer only on the raw chain context. "
    "Please return: (1) a brief summary, (2) key observations from the skew, and (3) a trading view."
)
MAX_CONTEXT_CHARS = 5000  # Reduced for Groq free tier TPM limits


def build_baseline_prompt(csv_path: str | Path | None = None) -> tuple[str, bool, int]:
    """Construct the raw prompt and expose whether the CSV context was truncated."""
    prompt = DEFAULT_PROMPT
    truncated = False
    original_length = 0

    if csv_path is not None:
        path = Path(csv_path)
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = "<unable to read CSV file>"
            original_length = len(text)
            if len(text) > MAX_CONTEXT_CHARS:
                truncated = True
                text = text[:MAX_CONTEXT_CHARS]
            prompt = (
                f"{DEFAULT_PROMPT}\n\n"
                f"CSV_PATH: {path}\n\n"
                f"RAW_OPTION_CHAIN_CSV:\n{text}"
            )

    return prompt, truncated, original_length


def baseline_agent_response(
    csv_path: str | Path | None = None,
    model: str = "openai/gpt-oss-20b",
) -> dict[str, Any]:
    """Use a single Anthropic call to answer the prompt without any tool use or calc layer."""
    prompt, truncated, original_length = build_baseline_prompt(csv_path)
    result: dict[str, Any] = {
        "agent": "baseline",
        "model": model,
        "mode": "direct_prompt_only",
        "prompt": prompt,
        "truncated": truncated,
        "original_length": original_length,
        "response": None,
        "error": None,
        "notes": [
            "No tool calls were used.",
            "No deterministic calc layer was invoked.",
            "This baseline is intentionally naive and meant to contrast with a tool-using agent.",
        ],
    }

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        result["error"] = {
            "type": "missing_api_key",
            "message": "GROQ_API_KEY is not set. Export it before calling the baseline agent.",
        }
        return result

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )
    except APITimeoutError as exc:
        result["error"] = {"type": "timeout", "message": str(exc)}
        return result
    except RateLimitError as exc:
        result["error"] = {"type": "rate_limit", "message": str(exc)}
        return result
    except APIStatusError as exc:
        result["error"] = {"type": "api_status_error", "message": str(exc)}
        return result
    except Exception as exc:  # pragma: no cover - defensive fallback for malformed runtime issues
        result["error"] = {"type": "api_call_failed", "message": str(exc)}
        return result

    try:
        result["response"] = response.choices[0].message.content or ""
    except Exception as exc:
        result["error"] = {"type": "malformed_response", "message": f"Groq response was malformed: {exc}"}
        return result

    if not result["response"]:
        result["error"] = {"type": "empty_response", "message": "Groq returned an empty text response."}

    return result


if __name__ == "__main__":
    print(json.dumps(baseline_agent_response(), indent=2, default=str))
