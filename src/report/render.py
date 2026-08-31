"""
Rendering utilities for skew curves and analysis reports.
Produces matplotlib plots for intraday skew evolution and day-to-day comparisons.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


def plot_skew_curve(
    skew_df: pd.DataFrame,
    title: str | None = None,
    output_path: str | Path | None = None,
    figsize: tuple[int, int] = (12, 6),
) -> str | None:
    """Plot intraday skew_25d evolution.
    
    Args:
        skew_df: Skew DataFrame with timestamp and skew_25d columns
        title: Plot title; if None, auto-generate from date
        output_path: Path to save PNG; if None, return base64 string (not implemented)
        figsize: Figure size (width, height)
        
    Returns:
        Path to saved file if output_path provided, else None
    """
    if skew_df is None or skew_df.empty:
        return None

    df = skew_df.copy()
    if "timestamp" not in df.columns or "skew_25d" not in df.columns:
        return None

    df = df.sort_values("timestamp").reset_index(drop=True)
    valid = df[df["skew_25d"].notna()].copy()
    if valid.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    # Plot skew curve.
    ax.plot(
        valid["timestamp"],
        valid["skew_25d"],
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=4,
        color="#1f77b4",
        alpha=0.8,
        label="25Δ Skew (PE IV - CE IV)",
    )

    # Add horizontal reference at zero.
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)

    # Formatting.
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Skew (IV points)", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=10)

    # Format x-axis as time.
    if pd.api.types.is_datetime64_any_dtype(valid["timestamp"]):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45, ha="right")

    # Title.
    if title is None:
        if not valid.empty:
            date_str = pd.Timestamp(valid.iloc[0]["timestamp"]).strftime("%Y-%m-%d")
            title = f"Nifty 25Δ Skew Curve ({date_str})"
        else:
            title = "Skew Curve"

    ax.set_title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()

    # Save or return.
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(output_path)

    plt.close(fig)
    return None


def plot_skew_comparison(
    prior_skew: pd.DataFrame,
    today_skew: pd.DataFrame,
    prior_date: str,
    today_date: str,
    output_path: str | Path | None = None,
    figsize: tuple[int, int] = (12, 6),
) -> str | None:
    """Plot prior-day and today's skew curves overlaid for comparison.
    
    Args:
        prior_skew: Prior day's skew DataFrame
        today_skew: Today's skew DataFrame
        prior_date: ISO date string for prior day
        today_date: ISO date string for today
        output_path: Path to save PNG; if None, return None
        figsize: Figure size (width, height)
        
    Returns:
        Path to saved file if output_path provided, else None
    """
    if (prior_skew is None or today_skew is None or 
        prior_skew.empty or today_skew.empty):
        return None

    if "timestamp" not in prior_skew.columns or "skew_25d" not in prior_skew.columns:
        return None
    if "timestamp" not in today_skew.columns or "skew_25d" not in today_skew.columns:
        return None

    prior_df = prior_skew.copy().sort_values("timestamp").reset_index(drop=True)
    today_df = today_skew.copy().sort_values("timestamp").reset_index(drop=True)

    prior_valid = prior_df[prior_df["skew_25d"].notna()].copy()
    today_valid = today_df[today_df["skew_25d"].notna()].copy()

    if prior_valid.empty or today_valid.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    # Plot both curves.
    ax.plot(
        prior_valid["timestamp"],
        prior_valid["skew_25d"],
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=4,
        color="#ff7f0e",
        alpha=0.7,
        label=f"Prior ({prior_date})",
    )
    ax.plot(
        today_valid["timestamp"],
        today_valid["skew_25d"],
        marker="s",
        linestyle="-",
        linewidth=2,
        markersize=4,
        color="#1f77b4",
        alpha=0.8,
        label=f"Today ({today_date})",
    )

    # Reference at zero.
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)

    # Formatting.
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Skew (IV points)", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=10)

    if pd.api.types.is_datetime64_any_dtype(prior_valid["timestamp"]):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45, ha="right")

    ax.set_title(f"Skew Comparison: {prior_date} vs {today_date}", 
                 fontsize=12, fontweight="bold")
    plt.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(output_path)

    plt.close(fig)
    return None
