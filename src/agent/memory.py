"""
Memory layer: carry forward prior-day skew curves for delta analysis.
Enables the agent to comment on change, not just a snapshot.

NOTE: interpolate_25delta_skew returns timestamp, iv_25d_CE, iv_25d_PE, skew_25d
WITHOUT per-expiry tracking. This is an EOD-style summary. If per-expiry tracking
is needed for comparison, skew.py should be modified to preserve expiry column.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def summarize_daily_skew(skew_df: pd.DataFrame) -> dict[str, Any]:
    """Summarize a day's skew session into close and summary statistics.
    
    Takes the full intraday skew_df and reduces it to:
    - Last (end-of-day) skew_25d value and timestamp
    - Mean, min, max skew_25d across the session
    - Last iv_25d_CE and iv_25d_PE values
    
    Args:
        skew_df: Skew DataFrame from interpolate_25delta_skew (columns: timestamp, 
                 iv_25d_CE, iv_25d_PE, skew_25d)
    
    Returns:
        Summary dict with close, mean, min, max, and EOD IV values
    """
    if skew_df is None or skew_df.empty:
        return {
            "error": "skew_df is None or empty",
            "close_value": None,
            "close_time": None,
            "mean": None,
            "min": None,
            "max": None,
            "close_ce_iv": None,
            "close_pe_iv": None,
        }

    df = skew_df.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Filter to rows with valid skew_25d.
    valid = df[df["skew_25d"].notna()].copy()
    if valid.empty:
        return {
            "error": "No valid skew_25d values in skew_df",
            "close_value": None,
            "close_time": None,
            "mean": None,
            "min": None,
            "max": None,
            "close_ce_iv": None,
            "close_pe_iv": None,
        }

    # Last row is the close.
    last_row = valid.iloc[-1]
    close_value = float(last_row["skew_25d"])
    close_time = str(last_row["timestamp"])
    close_ce_iv = float(last_row["iv_25d_CE"]) if pd.notna(last_row["iv_25d_CE"]) else None
    close_pe_iv = float(last_row["iv_25d_PE"]) if pd.notna(last_row["iv_25d_PE"]) else None

    # Summary stats.
    mean_skew = float(valid["skew_25d"].mean())
    min_skew = float(valid["skew_25d"].min())
    max_skew = float(valid["skew_25d"].max())

    return {
        "error": None,
        "close_value": close_value,
        "close_time": close_time,
        "mean": mean_skew,
        "min": min_skew,
        "max": max_skew,
        "close_ce_iv": close_ce_iv,
        "close_pe_iv": close_pe_iv,
        "row_count": int(valid.shape[0]),
    }


class SkewMemory:
    """Store and compare skew curves across trading days."""

    def __init__(self, memory_dir: str | Path = ".cache/skew_memory"):
        """Initialize memory store.
        
        Args:
            memory_dir: Directory to persist skew snapshots (default: .cache/skew_memory)
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _get_snapshot_path(self, date_str: str) -> Path:
        """Get file path for a date's skew snapshot (parquet).
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD)
            
        Returns:
            Path to the snapshot parquet file
        """
        return self.memory_dir / f"skew_{date_str}.parquet"

    def _get_summary_path(self, date_str: str) -> Path:
        """Get file path for a date's skew summary (JSON).
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD)
            
        Returns:
            Path to the summary JSON file
        """
        return self.memory_dir / f"skew_{date_str}_summary.json"

    def save_skew(self, skew_df: pd.DataFrame, date_str: str | None = None) -> dict[str, Any]:
        """Save today's skew curve (full data) and summary for future comparison.
        
        Args:
            skew_df: Skew DataFrame (from interpolate_25delta_skew)
            date_str: ISO date string; if None, use today's date
            
        Returns:
            Status dict with paths and summary
        """
        if skew_df is None or skew_df.empty:
            return {"saved": False, "error": "skew_df is None or empty"}

        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Save raw parquet.
        parquet_path = self._get_snapshot_path(date_str)
        try:
            skew_df.to_parquet(parquet_path)
        except Exception as e:
            return {"saved": False, "error": f"Failed to save parquet: {str(e)}"}

        # Compute and save summary JSON.
        summary = summarize_daily_skew(skew_df)
        summary_path = self._get_summary_path(date_str)
        try:
            with open(summary_path, "w") as f:
                json.dump(summary, f, default=str, indent=2)
        except Exception as e:
            return {"saved": False, "error": f"Failed to save summary: {str(e)}"}

        return {
            "saved": True,
            "date": date_str,
            "parquet_path": str(parquet_path),
            "summary_path": str(summary_path),
            "rows": len(skew_df),
            "summary": summary,
        }

    def load_prior_skew(self, date_str: str) -> pd.DataFrame | None:
        """Load skew curve from a prior date (raw parquet).
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD)
            
        Returns:
            Skew DataFrame or None if not found
        """
        path = self._get_snapshot_path(date_str)
        if not path.exists():
            return None
        try:
            return pd.read_parquet(path)
        except Exception:
            return None

    def load_prior_skew_summary(self, date_str: str) -> dict[str, Any] | None:
        """Load skew summary from a prior date (JSON).
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD)
            
        Returns:
            Summary dict or None if not found
        """
        path = self._get_summary_path(date_str)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def get_latest_prior_skew_summary(self, current_date_str: str) -> tuple[str | None, dict[str, Any] | None]:
        """Load the most recent skew summary before the given date.
        
        Args:
            current_date_str: ISO format date string (YYYY-MM-DD)
            
        Returns:
            Tuple of (prior_date_str, prior_summary_dict) or (None, None) if not found
        """
        summary_files = sorted(self.memory_dir.glob("skew_*_summary.json"))
        if not summary_files:
            return None, None

        # Extract dates and filter those before current_date_str.
        current_dt = datetime.fromisoformat(current_date_str)
        prior_candidates = []
        for fpath in summary_files:
            try:
                # Extract date from skew_YYYY-MM-DD_summary.json
                date_str = fpath.stem.replace("skew_", "").replace("_summary", "")
                file_dt = datetime.fromisoformat(date_str)
                if file_dt < current_dt:
                    prior_candidates.append((date_str, fpath))
            except ValueError:
                continue

        if not prior_candidates:
            return None, None

        # Return the most recent prior date.
        prior_date_str, prior_path = sorted(prior_candidates, key=lambda x: x[0], reverse=True)[0]
        try:
            with open(prior_path, "r") as f:
                prior_summary = json.load(f)
            return prior_date_str, prior_summary
        except Exception:
            return None, None

    def compare_skews(
        self,
        today_summary: dict[str, Any],
        prior_summary: dict[str, Any],
        today_date: str,
        prior_date: str,
    ) -> dict[str, Any]:
        """Compare today's skew summary to prior skew summary; compute deltas.
        
        Compares close-to-close skew_25d values and mean-to-mean changes.
        
        Args:
            today_summary: Today's skew summary (from summarize_daily_skew)
            prior_summary: Prior day's skew summary
            today_date: ISO date string for today
            prior_date: ISO date string for prior day
            
        Returns:
            Comparison dict with close-to-close and mean-to-mean deltas
        """
        if today_summary is None or prior_summary is None:
            return {"error": "One or both summary dicts are None"}

        if today_summary.get("error") or prior_summary.get("error"):
            return {
                "error": "One or both summaries have errors",
                "today_error": today_summary.get("error"),
                "prior_error": prior_summary.get("error"),
            }

        today_close = today_summary.get("close_value")
        prior_close = prior_summary.get("close_value")
        today_mean = today_summary.get("mean")
        prior_mean = prior_summary.get("mean")

        if today_close is None or prior_close is None:
            return {"error": "Missing close_value in one or both summaries"}

        # Close-to-close comparison.
        close_change = today_close - prior_close
        close_pct_change = (close_change / abs(prior_close)) * 100 if prior_close != 0 else None

        # Mean-to-mean comparison (if available).
        mean_change = None
        mean_pct_change = None
        if today_mean is not None and prior_mean is not None:
            mean_change = today_mean - prior_mean
            mean_pct_change = (mean_change / abs(prior_mean)) * 100 if prior_mean != 0 else None

        # IV component changes.
        today_ce = today_summary.get("close_ce_iv")
        prior_ce = prior_summary.get("close_ce_iv")
        ce_change = (today_ce - prior_ce) if (today_ce is not None and prior_ce is not None) else None

        today_pe = today_summary.get("close_pe_iv")
        prior_pe = prior_summary.get("close_pe_iv")
        pe_change = (today_pe - prior_pe) if (today_pe is not None and prior_pe is not None) else None

        return {
            "status": "compared",
            "today_date": today_date,
            "prior_date": prior_date,
            "close_to_close": {
                "prior_close": float(prior_close),
                "today_close": float(today_close),
                "change": float(close_change),
                "pct_change": float(close_pct_change) if close_pct_change is not None else None,
            },
            "mean_to_mean": {
                "prior_mean": float(prior_mean) if prior_mean is not None else None,
                "today_mean": float(today_mean) if today_mean is not None else None,
                "change": float(mean_change) if mean_change is not None else None,
                "pct_change": float(mean_pct_change) if mean_pct_change is not None else None,
            },
            "iv_components": {
                "ce_change": float(ce_change) if ce_change is not None else None,
                "pe_change": float(pe_change) if pe_change is not None else None,
            },
            "range_context": {
                "prior_range": {
                    "min": float(prior_summary.get("min")) if prior_summary.get("min") is not None else None,
                    "max": float(prior_summary.get("max")) if prior_summary.get("max") is not None else None,
                },
                "today_range": {
                    "min": float(today_summary.get("min")) if today_summary.get("min") is not None else None,
                    "max": float(today_summary.get("max")) if today_summary.get("max") is not None else None,
                },
            },
        }

    def get_memory_summary(self) -> dict[str, Any]:
        """List all stored skew snapshots and their metadata.
        
        Returns:
            Summary dict with snapshot dates and row counts
        """
        summary_files = sorted(self.memory_dir.glob("skew_*_summary.json"))
        snapshots = []
        for fpath in summary_files:
            try:
                date_str = fpath.stem.replace("skew_", "").replace("_summary", "")
                with open(fpath, "r") as f:
                    summary = json.load(f)
                snapshots.append({
                    "date": date_str,
                    "summary_path": str(fpath),
                    "close_value": summary.get("close_value"),
                    "mean": summary.get("mean"),
                    "row_count": summary.get("row_count"),
                })
            except Exception as e:
                snapshots.append({
                    "date": fpath.stem.replace("skew_", "").replace("_summary", ""),
                    "path": str(fpath),
                    "error": str(e),
                })

        return {
            "memory_dir": str(self.memory_dir),
            "snapshot_count": len(snapshots),
            "snapshots": snapshots,
        }


def build_memory_context(
    today_skew: pd.DataFrame,
    memory: SkewMemory | None = None,
    today_date: str | None = None,
) -> dict[str, Any]:
    """Build a context dict for the agent: today's skew summary + prior deltas.
    
    This is a convenience function to pre-compute memory context before
    handing it to the agent in session_state.
    
    Args:
        today_skew: Today's skew DataFrame (from interpolate_25delta_skew)
        memory: SkewMemory instance; if None, create a default one
        today_date: ISO date string; if None, use today
        
    Returns:
        Context dict with today_summary, prior_date, comparison, etc.
    """
    if memory is None:
        memory = SkewMemory()

    if today_date is None:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Summarize today's skew.
    today_summary = summarize_daily_skew(today_skew) if today_skew is not None else None

    context = {
        "today_date": today_date,
        "today_summary": today_summary,
    }

    # Try to load and compare with prior summary.
    prior_date, prior_summary = memory.get_latest_prior_skew_summary(today_date)
    if (prior_date is not None and prior_summary is not None and 
        today_summary is not None and today_summary.get("error") is None):
        comparison = memory.compare_skews(today_summary, prior_summary, today_date, prior_date)
        context["prior_date"] = prior_date
        context["comparison"] = comparison
    else:
        context["prior_date"] = None
        context["comparison"] = None

    # Optionally save today's skew for tomorrow's comparison.
    if today_skew is not None and not today_skew.empty:
        save_result = memory.save_skew(today_skew, today_date)
        context["save_status"] = save_result

    return context
