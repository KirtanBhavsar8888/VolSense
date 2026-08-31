"""
Report agent: synthesizes analysis results into markdown reports and plots.
Takes verified analysis session state and produces structured output for stakeholders.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.report.render import plot_skew_curve, plot_skew_comparison


def build_markdown_report(
    agent_response: dict[str, Any],
    session_state: dict[str, Any],
    memory_context: dict[str, Any] | None = None,
    analysis_date: str | None = None,
) -> str:
    """Build a markdown report from agent analysis, session state, and memory context.
    
    Args:
        agent_response: Output from run_analysis_agent (includes final_response, tool_trace)
        session_state: Session state dict with chain_df, futures_df, iv_delta_df, skew_df
        memory_context: Optional memory context with prior comparisons
        analysis_date: ISO date string; if None, use today
        
    Returns:
        Markdown string ready for display or file output
    """
    if analysis_date is None:
        analysis_date = datetime.utcnow().strftime("%Y-%m-%d")

    lines = [
        f"# Nifty Options Skew Analysis Report",
        f"**Date**: {analysis_date}",
        "",
    ]

    # Analysis Summary
    lines.extend([
        "## Analysis Summary",
        "",
    ])

    if agent_response.get("status") == "reroute":
        lines.append(f"⚠️ **Status**: Chain validation reroute")
        lines.append(f"**Reason**: {agent_response.get('reason', 'N/A')}")
        lines.append("")
        sanity_details = agent_response.get("sanity", {}).get("details", {})
        if sanity_details.get("issues"):
            lines.append("**Issues flagged**:")
            for issue in sanity_details["issues"]:
                lines.append(f"  - {issue}")
        lines.append("")
        return "\n".join(lines)

    # Normal analysis path.
    final_response = agent_response.get("final_response", "").strip()
    if final_response:
        lines.extend([
            "### Agent Analysis",
            "",
            final_response,
            "",
        ])

    # Tool Trace Summary
    tool_trace = agent_response.get("tool_trace", [])
    if tool_trace:
        lines.extend([
            "## Tool Execution Trace",
            "",
        ])
        for i, trace in enumerate(tool_trace, 1):
            tool_name = trace.get("tool", "unknown")
            tool_output = trace.get("output", {})
            
            if isinstance(tool_output, dict) and tool_output.get("error"):
                status = "❌ Error"
                error_msg = tool_output["error"]
                lines.append(f"### Tool {i}: {tool_name} {status}")
                lines.append(f"**Error**: {error_msg}")
            else:
                status = "✓ Success"
                lines.append(f"### Tool {i}: {tool_name} {status}")
            
            lines.append("")

    # Memory Context: Prior Day Comparison
    if memory_context is not None and memory_context.get("comparison") is not None:
        comparison = memory_context["comparison"]
        if comparison.get("status") == "compared":
            lines.extend([
                "## Day-over-Day Comparison",
                "",
            ])
            
            prior_date = memory_context.get("prior_date", "N/A")
            lines.append(f"**Prior Date**: {prior_date}")
            lines.append("")

            # Close-to-close.
            close_data = comparison.get("close_to_close", {})
            if close_data:
                prior_close = close_data.get("prior_close")
                today_close = close_data.get("today_close")
                change = close_data.get("change")
                pct_change = close_data.get("pct_change")

                lines.append("### Close-to-Close Skew Change")
                lines.append(f"- **{prior_date} Close**: {prior_close:.4f}")
                lines.append(f"- **{analysis_date} Close**: {today_close:.4f}")
                if change is not None:
                    arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    lines.append(f"- **Change**: {arrow} {change:+.4f} ({pct_change:+.2f}%)")
                lines.append("")

            # Mean-to-mean.
            mean_data = comparison.get("mean_to_mean", {})
            if mean_data and mean_data.get("prior_mean") is not None:
                lines.append("### Intraday Mean Skew Change")
                lines.append(f"- **{prior_date} Mean**: {mean_data['prior_mean']:.4f}")
                lines.append(f"- **{analysis_date} Mean**: {mean_data['today_mean']:.4f}")
                if mean_data.get("change") is not None:
                    arrow = "📈" if mean_data["change"] > 0 else "📉" if mean_data["change"] < 0 else "➡️"
                    lines.append(f"- **Change**: {arrow} {mean_data['change']:+.4f}")
                lines.append("")

            # IV components.
            iv_comps = comparison.get("iv_components", {})
            if iv_comps.get("ce_change") is not None or iv_comps.get("pe_change") is not None:
                lines.append("### IV Component Changes (Close-to-Close)")
                if iv_comps.get("ce_change") is not None:
                    lines.append(f"- **Call IV (25Δ)**: {iv_comps['ce_change']:+.4f}")
                if iv_comps.get("pe_change") is not None:
                    lines.append(f"- **Put IV (25Δ)**: {iv_comps['pe_change']:+.4f}")
                lines.append("")

            # Range context.
            range_ctx = comparison.get("range_context", {})
            if range_ctx:
                lines.append("### Session Range Context")
                prior_range = range_ctx.get("prior_range", {})
                today_range = range_ctx.get("today_range", {})
                
                prior_min = prior_range.get("min")
                prior_max = prior_range.get("max")
                today_min = today_range.get("min")
                today_max = today_range.get("max")
                
                prior_min_str = f"{prior_min:.4f}" if prior_min is not None else "N/A"
                prior_max_str = f"{prior_max:.4f}" if prior_max is not None else "N/A"
                today_min_str = f"{today_min:.4f}" if today_min is not None else "N/A"
                today_max_str = f"{today_max:.4f}" if today_max is not None else "N/A"
                
                lines.append(f"- **{prior_date}**: min {prior_min_str}, max {prior_max_str}")
                lines.append(f"- **{analysis_date}**: min {today_min_str}, max {today_max_str}")
                lines.append("")

    # Session State Summary
    lines.extend([
        "## Session State Summary",
        "",
    ])

    chain_df = session_state.get("chain_df")
    futures_df = session_state.get("futures_df")
    iv_delta_df = session_state.get("iv_delta_df")
    skew_df = session_state.get("skew_df")

    if chain_df is not None and not chain_df.empty:
        lines.append(f"- **Option Chain Rows**: {len(chain_df)}")
    if futures_df is not None and not futures_df.empty:
        lines.append(f"- **Synthetic Futures**: {len(futures_df)}")
    if iv_delta_df is not None and not iv_delta_df.empty:
        lines.append(f"- **IV/Delta Rows**: {len(iv_delta_df)}")
    if skew_df is not None and not skew_df.empty:
        lines.append(f"- **Skew Samples**: {len(skew_df)}")

    lines.extend([
        "",
        "---",
        f"*Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*",
    ])

    return "\n".join(lines)


def generate_report(
    agent_response: dict[str, Any],
    session_state: dict[str, Any],
    memory_context: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
    analysis_date: str | None = None,
) -> dict[str, Any]:
    """Generate a complete report: markdown + plots.
    
    Args:
        agent_response: Output from run_analysis_agent
        session_state: Session state dict
        memory_context: Optional memory context with prior comparisons
        output_dir: Directory to save report files; if None, skip file I/O
        analysis_date: ISO date string; if None, use today
        
    Returns:
        Status dict with report content and file paths
    """
    if analysis_date is None:
        analysis_date = datetime.utcnow().strftime("%Y-%m-%d")

    result = {
        "date": analysis_date,
        "markdown_content": None,
        "markdown_path": None,
        "plot_paths": [],
        "errors": [],
    }

    # Build markdown.
    try:
        markdown = build_markdown_report(
            agent_response,
            session_state,
            memory_context,
            analysis_date,
        )
        result["markdown_content"] = markdown
    except Exception as e:
        result["errors"].append(f"Markdown generation failed: {str(e)}")

    # Save markdown if output_dir provided.
    if output_dir is not None and result["markdown_content"] is not None:
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            markdown_path = output_dir / f"report_{analysis_date}.md"
            markdown_path.write_text(result["markdown_content"])
            result["markdown_path"] = str(markdown_path)
        except Exception as e:
            result["errors"].append(f"Failed to save markdown: {str(e)}")

    # Generate plots.
    skew_df = session_state.get("skew_df")

    # Today's skew curve.
    if skew_df is not None and not skew_df.empty and output_dir is not None:
        try:
            plot_path = Path(output_dir) / f"skew_curve_{analysis_date}.png"
            plot_file = plot_skew_curve(
                skew_df,
                title=f"Nifty 25Δ Skew Curve ({analysis_date})",
                output_path=plot_path,
            )
            if plot_file:
                result["plot_paths"].append(plot_file)
        except Exception as e:
            result["errors"].append(f"Skew curve plot failed: {str(e)}")

    # Comparison plot (if prior skew available).
    if (memory_context is not None and 
        memory_context.get("comparison") is not None and 
        output_dir is not None):
        try:
            prior_date = memory_context.get("prior_date")
            comparison = memory_context.get("comparison", {})
            
            # Try to load prior skew from memory.
            if prior_date is not None:
                from src.agent.memory import SkewMemory
                memory = SkewMemory()
                prior_skew = memory.load_prior_skew(prior_date)
                
                if prior_skew is not None and skew_df is not None and not skew_df.empty:
                    plot_path = Path(output_dir) / f"skew_comparison_{prior_date}_vs_{analysis_date}.png"
                    plot_file = plot_skew_comparison(
                        prior_skew,
                        skew_df,
                        prior_date,
                        analysis_date,
                        output_path=plot_path,
                    )
                    if plot_file:
                        result["plot_paths"].append(plot_file)
        except Exception as e:
            result["errors"].append(f"Comparison plot failed: {str(e)}")

    return result
