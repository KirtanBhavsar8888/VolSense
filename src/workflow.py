"""Shared end-to-end analysis workflow used by the CLI pipeline and the API."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from src.agent.analysis_agent import run_analysis_agent
from src.agent.baseline import baseline_agent_response
from src.agent.deterministic import run_deterministic_analysis
from src.agent.memory import SkewMemory, build_memory_context
from src.agent.report_agent import generate_report
from src.data_io import DEFAULT_CSV_PATH, ensure_sample_csv, load_chain
from src.db.operations import (
    add_daily_comparison,
    add_evaluation_result,
    add_skew_snapshot,
    store_agent_result,
    store_baseline_result,
    store_eval_score,
    store_error,
    update_session_status,
)
from src.json_util import json_safe

logger = logging.getLogger(__name__)


def _close_skew(skew_df: pd.DataFrame | None) -> float | None:
    if skew_df is None or skew_df.empty or "skew_25d" not in skew_df.columns:
        return None
    valid = skew_df[skew_df["skew_25d"].notna()]
    if valid.empty:
        return None
    return float(valid.iloc[-1]["skew_25d"])


def persist_skew_snapshots(session_id: str, skew_df: pd.DataFrame | None, db: Session | None) -> None:
    if db is None or skew_df is None or skew_df.empty:
        return
    valid = skew_df[skew_df["skew_25d"].notna()].copy()
    for _, row in valid.iterrows():
        timestamp = pd.to_datetime(row["timestamp"]) if "timestamp" in row else datetime.utcnow()
        bar_time = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
        add_skew_snapshot(
            session_id=session_id,
            strike=float(row["iv_25d_PE"]) if pd.notna(row.get("iv_25d_PE")) else 0.0,
            skew_value=float(row["skew_25d"]),
            delta=0.25,
            iv=float(row["iv_25d_CE"]) if pd.notna(row.get("iv_25d_CE")) else None,
            date=bar_time,
            db=db,
        )


def run_evaluation(session_id: str, db: Session | None) -> float:
    """Score eval/cases.json with the deterministic calc layer (no extra LLM calls)."""
    from eval.run_eval import chain_snippet_to_df, load_cases, score_case

    cases = load_cases()
    passed_cases = 0
    total_cases = len(cases)

    for case in cases:
        case_id = case.get("case_id", "unknown")
        difficulty = case.get("difficulty", "unknown")
        try:
            chain_df = chain_snippet_to_df(case.get("chain_snippet", {}))
            agent_result = run_deterministic_analysis(chain_df)
            baseline_result = {"error": None, "final_response": "deterministic-eval"}
            score = score_case(case, baseline_result, agent_result)
            case_passed = score["failed"] == 0
            if case_passed:
                passed_cases += 1
            close = agent_result.get("close_skew")
            if close is None:
                close = _close_skew((agent_result.get("session_state") or {}).get("skew_df"))
            expected = 1.0 if case_passed else 0.0
            actual = float(close) if close is not None else 0.0
            if db is not None:
                add_evaluation_result(
                    session_id=session_id,
                    case_id=case_id,
                    difficulty=difficulty,
                    expected_skew=expected,
                    actual_skew=actual,
                    passed=case_passed,
                    error_margin=float(score["failed"]),
                    db=db,
                )
            logger.info(
                "  %s: %s (%s/%s checks)",
                case_id,
                "PASS" if case_passed else "FAIL",
                score["passed"],
                score["passed"] + score["failed"],
            )
        except Exception as exc:
            logger.warning("  %s: Error - %s", case_id, exc)

    return (passed_cases / total_cases * 100) if total_cases else 0.0


def run_full_pipeline(
    session_id: str,
    csv_path: str | Path = DEFAULT_CSV_PATH,
    db: Session | None = None,
    skip_database: bool = False,
) -> dict[str, Any]:
    """Run baseline (if keyed), calc tools, optional LLM agent, eval, and report."""
    csv_path = str(ensure_sample_csv(csv_path))
    chain_df = load_chain(csv_path)
    use_db = db is not None and not skip_database

    if use_db:
        update_session_status(session_id, "running", db)

    try:
        calc_result = run_deterministic_analysis(chain_df)
        live_state = calc_result.get("session_state") or {}
        skew_df = live_state.get("skew_df")
        memory_context = build_memory_context(skew_df)
        close = calc_result.get("close_skew") or _close_skew(skew_df)

        api_key = os.getenv("GROQ_API_KEY")
        baseline_result = baseline_agent_response(csv_path)
        if api_key:
            try:
                agent_result = run_analysis_agent(chain_df)
            except Exception as e:
                logger.warning(f"Analysis agent failed, falling back to deterministic: {e}")
                agent_result = calc_result
            if (agent_result.get("session_state") or {}).get("skew_df") is None:
                agent_result = {
                    **agent_result,
                    "session_state": live_state,
                    "tool_trace": agent_result.get("tool_trace") or calc_result.get("tool_trace"),
                    "close_skew": close,
                    "calc": {
                        "agent": "deterministic",
                        "final_response": calc_result.get("final_response"),
                        "close_skew": close,
                    },
                }
            else:
                live_state = agent_result.get("session_state") or live_state
                skew_df = live_state.get("skew_df")
                memory_context = build_memory_context(skew_df)
                close = _close_skew(skew_df)
                agent_result["close_skew"] = close
        else:
            agent_result = calc_result

        if use_db:
            store_baseline_result(session_id, json_safe(baseline_result), db)
            store_agent_result(session_id, json_safe(agent_result), db)
            persist_skew_snapshots(session_id, skew_df, db)
            if close is not None:
                add_daily_comparison(
                    date=datetime.utcnow(),
                    baseline_skew=float(close),
                    agent_skew=float(close),
                    baseline_confidence=None,
                    agent_confidence=1.0 if agent_result.get("agent") == "deterministic" else None,
                    db=db,
                )

        eval_score = run_evaluation(session_id, db if use_db else None)
        if use_db:
            store_eval_score(session_id, eval_score, db)

        report = generate_report(
            agent_response=agent_result,
            session_state=live_state,
            memory_context=memory_context,
            output_dir=Path("reports") / session_id,
        )
        markdown = report.get("markdown_content") or ""
        report_path = report.get("markdown_path")
        if markdown and not report_path:
            out_dir = Path("reports")
            out_dir.mkdir(exist_ok=True)
            dest = out_dir / f"report_{session_id}.md"
            dest.write_text(markdown, encoding="utf-8")
            report_path = str(dest)

        if use_db:
            update_session_status(session_id, "completed", db)

        return {
            "session_id": session_id,
            "baseline_result": json_safe(baseline_result),
            "agent_result": json_safe(agent_result),
            "eval_score": eval_score,
            "report_path": report_path,
            "close_skew": close,
            "rows": int(len(chain_df)),
            "used_llm": bool(api_key),
        }
    except Exception as exc:
        logger.exception("Pipeline failed")
        if use_db:
            store_error(session_id, str(exc), db)
        raise
