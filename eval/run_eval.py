"""
Evaluation framework: score baseline and agent against known-correct reference cases.
Runs both implementations and compares outputs.
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.agent.baseline import baseline_agent_response
from src.agent.analysis_agent import run_analysis_agent
from src.verification.bounds_check import flag_bad_chain


def load_cases(cases_file: str | Path = "eval/cases.json") -> list[dict[str, Any]]:
    """Load test cases from JSON file.
    
    Args:
        cases_file: Path to cases.json
        
    Returns:
        List of case dicts
    """
    with open(cases_file, "r") as f:
        return json.load(f)


def chain_snippet_to_df(snippet: dict[str, Any]) -> pd.DataFrame:
    """Convert a case's chain_snippet to a pandas DataFrame.
    
    Args:
        snippet: Dict with timestamp and rows
        
    Returns:
        DataFrame with all required columns
    """
    rows = snippet.get("rows", [])
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    
    # Ensure datetime columns.
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "expiry" in df.columns:
        df["expiry"] = pd.to_datetime(df["expiry"])
    
    return df


def score_case(
    case: dict[str, Any],
    baseline_result: dict[str, Any],
    agent_result: dict[str, Any],
) -> dict[str, Any]:
    """Score a single case: check expected outputs against actual results.
    
    Args:
        case: Case dict with expected_outputs
        baseline_result: Result from baseline_agent_response
        agent_result: Result from run_analysis_agent
        
    Returns:
        Scoring dict with passed/failed checks
    """
    expected = case.get("expected_outputs", {})
    scores = {
        "case_id": case.get("case_id"),
        "difficulty": case.get("difficulty", "unknown"),
        "checks": {},
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    # Helper to check and record a boolean expectation.
    def check(key: str, actual: bool, expected_val: bool | None = None):
        if expected_val is None:
            return  # Skip if not specified.
        
        passed = actual == expected_val
        scores["checks"][key] = {
            "expected": expected_val,
            "actual": actual,
            "passed": passed,
        }
        if passed:
            scores["passed"] += 1
        else:
            scores["failed"] += 1

    # Sanity check (bounds_check).
    if "sanity_check_pass" in expected:
        sanity_pass = agent_result.get("status") != "reroute"
        check("sanity_check_pass", sanity_pass, expected.get("sanity_check_pass"))

    # Reroute status.
    if "reroute_status" in expected:
        reroute_status = agent_result.get("status")
        expected_status = expected.get("reroute_status")
        matched = reroute_status == expected_status or (
            expected_status in {"fail", "reroute"} and reroute_status in {"fail", "reroute"}
        )
        check("reroute_status", matched, True)

    # Reason substring check.
    if "reason_contains" in expected:
        reason = agent_result.get("reason", "")
        contains = expected["reason_contains"].lower() in reason.lower()
        scores["checks"]["reason_contains"] = {
            "expected_substring": expected["reason_contains"],
            "actual_reason": reason,
            "passed": contains,
        }
        if contains:
            scores["passed"] += 1
        else:
            scores["failed"] += 1

    # Skew computed.
    if "skew_computed" in expected:
        skew_df = agent_result.get("session_state", {}).get("skew_df")
        skew_ok = skew_df is not None and not skew_df.empty
        check("skew_computed", skew_ok, expected.get("skew_computed"))

    # Skew sign.
    if "skew_sign" in expected:
        skew_df = agent_result.get("session_state", {}).get("skew_df")
        if skew_df is not None and not skew_df.empty and "skew_25d" in skew_df.columns:
            last_valid = skew_df[skew_df["skew_25d"].notna()]
            if not last_valid.empty:
                last_skew = last_valid.iloc[-1]["skew_25d"]
                if expected["skew_sign"] == "positive":
                    skew_ok = last_skew > 0
                elif expected["skew_sign"] == "negative":
                    skew_ok = last_skew < 0
                else:
                    skew_ok = True
                check("skew_sign", skew_ok, True)

    # Synthetic future ok.
    if "synthetic_future_ok" in expected:
        futures_df = agent_result.get("session_state", {}).get("futures_df")
        futures_ok = futures_df is not None and not futures_df.empty
        check("synthetic_future_ok", futures_ok, expected.get("synthetic_future_ok"))

    # IV/delta ok.
    if "iv_delta_ok" in expected:
        iv_delta_df = agent_result.get("session_state", {}).get("iv_delta_df")
        iv_ok = iv_delta_df is not None and not iv_delta_df.empty
        check("iv_delta_ok", iv_ok, expected.get("iv_delta_ok"))

    # DTE valid.
    if "dte_valid" in expected:
        chain_df = agent_result.get("session_state", {}).get("chain_df")
        dte_ok = chain_df is not None and not chain_df.empty and "dte" in chain_df.columns
        check("dte_valid", dte_ok, expected.get("dte_valid"))

    # Baseline and agent completion.
    if "baseline_completes" in expected:
        baseline_ok = baseline_result.get("error") is None and "final_response" in baseline_result
        check("baseline_completes", baseline_ok, expected.get("baseline_completes"))

    if "agent_completes" in expected:
        agent_ok = agent_result.get("error") is None and agent_result.get("status") != "reroute"
        check("agent_completes", agent_ok, expected.get("agent_completes"))

    if "both_agents_run" in expected:
        both_ok = ("final_response" in baseline_result) and ("final_response" in agent_result or agent_result.get("status") == "reroute")
        check("both_agents_run", both_ok, expected.get("both_agents_run"))

    return scores


def run_eval(
    cases_file: str | Path = "eval/cases.json",
    output_dir: str | Path | None = None,
    skip_agents: bool = False,
) -> dict[str, Any]:
    """Run evaluation on all test cases.
    
    Args:
        cases_file: Path to cases.json
        output_dir: Directory to save results; if None, skip file I/O
        skip_agents: If True, only validate sanity checks (faster testing)
        
    Returns:
        Evaluation summary dict
    """
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    cases = load_cases(cases_file)
    results = {
        "eval_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_cases": len(cases),
        "case_results": [],
        "summary": {
            "easy": {"passed": 0, "failed": 0},
            "medium": {"passed": 0, "failed": 0},
            "hard": {"passed": 0, "failed": 0},
        },
        "errors": [],
    }

    for case in cases:
        case_id = case.get("case_id", "unknown")
        difficulty = case.get("difficulty", "unknown")

        try:
            # Build DataFrame from snippet.
            chain_df = chain_snippet_to_df(case.get("chain_snippet", {}))
            if chain_df.empty:
                results["errors"].append(f"{case_id}: empty chain_df")
                continue

            # Run sanity check (always).
            sanity = flag_bad_chain(chain_df)

            # Run baseline and agent (if not skipped).
            baseline_result = None
            agent_result = None

            if not skip_agents:
                # baseline_agent_response expects a CSV file path, not a DataFrame.
                # Write chain_df to a temp CSV and pass the path.
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                        chain_df.to_csv(tmp, index=False)
                        tmp_path = tmp.name
                    baseline_result = baseline_agent_response(tmp_path)
                    os.unlink(tmp_path)  # Clean up temp file.
                except Exception as e:
                    baseline_result = {"error": str(e), "final_response": None}

                try:
                    agent_result = run_analysis_agent(chain_df)
                except Exception as e:
                    agent_result = {"error": str(e), "status": "error"}
            else:
                baseline_result = {"final_response": "(skipped)", "sanity": sanity}
                agent_result = {"final_response": "(skipped)", "sanity": sanity, "session_state": {"chain_df": chain_df, "futures_df": None, "iv_delta_df": None, "skew_df": None}}

            # Score the case.
            score = score_case(case, baseline_result or {}, agent_result or {})
            score["sanity"] = sanity

            results["case_results"].append(score)

            # Update summary.
            if difficulty in results["summary"]:
                results["summary"][difficulty]["passed"] += score["passed"]
                results["summary"][difficulty]["failed"] += score["failed"]

        except Exception as e:
            results["errors"].append(f"{case_id}: {str(e)}")

    # Compute overall totals.
    total_passed = sum(r["passed"] for r in results["case_results"])
    total_failed = sum(r["failed"] for r in results["case_results"])

    results["overall"] = {
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": (total_passed / (total_passed + total_failed)) if (total_passed + total_failed) > 0 else 0.0,
    }

    # Save results if output_dir provided.
    if output_dir is not None:
        results_file = output_dir / f"eval_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Also save a text summary.
        summary_file = output_dir / "eval_summary.txt"
        with open(summary_file, "w") as f:
            f.write("=== CCSPL Nifty Skew Agent Evaluation Summary ===\n\n")
            f.write(f"Date: {results['eval_date']}\n")
            f.write(f"Total Cases: {results['total_cases']}\n\n")
            f.write(f"Overall Pass Rate: {results['overall']['pass_rate']:.1%} ({total_passed}/{total_passed + total_failed})\n\n")
            f.write("By Difficulty:\n")
            for diff in ["easy", "medium", "hard"]:
                summary = results["summary"][diff]
                total = summary["passed"] + summary["failed"]
                if total > 0:
                    rate = summary["passed"] / total
                    f.write(f"  {diff}: {rate:.1%} ({summary['passed']}/{total})\n")
            f.write("\n")
            f.write("Case-by-case Results:\n")
            for score in results["case_results"]:
                status = "✓" if score["failed"] == 0 else "✗"
                f.write(f"  {status} {score['case_id']} ({score['difficulty']}): {score['passed']}/{score['passed'] + score['failed']} passed\n")

    return results


if __name__ == "__main__":
    import sys

    output_dir = "eval/results" if len(sys.argv) <= 1 else sys.argv[1]
    skip_agents = "--skip-agents" in sys.argv

    print(f"Running evaluation from eval/cases.json...")
    if skip_agents:
        print("(Skipping baseline and agent execution)")

    results = run_eval(output_dir=output_dir, skip_agents=skip_agents)

    print(f"\nOverall pass rate: {results['overall']['pass_rate']:.1%}")
    print(f"Results saved to {output_dir}")
