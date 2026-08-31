from __future__ import annotations

import numpy as np
import pandas as pd


def _interp_single_iv(sub: pd.DataFrame, target_delta: float, delta_range: tuple) -> float:
    """Interpolate a single IV level for one timestamp and one option side."""
    delta_min, delta_max = delta_range
    sub = sub.dropna(subset=["iv", "delta"]).copy()
    sub["abs_delta"] = sub["delta"].abs()
    sub = sub[(sub["abs_delta"] >= delta_min) & (sub["abs_delta"] <= delta_max)].copy()
    if len(sub) < 2:
        return np.nan

    sub = sub.sort_values("abs_delta").drop_duplicates("abs_delta")
    abs_deltas = sub["abs_delta"].to_numpy(dtype=float)
    ivs = sub["iv"].to_numpy(dtype=float)

    if target_delta < abs_deltas.min() or target_delta > abs_deltas.max():
        return np.nan

    idx_hi = np.searchsorted(abs_deltas, target_delta, side="right")
    idx_lo = idx_hi - 1
    if idx_lo < 0 or idx_hi >= len(abs_deltas):
        return np.nan

    if idx_lo >= 1:
        idxs = [idx_lo - 1, idx_lo, idx_hi]
    elif idx_hi + 1 < len(abs_deltas):
        idxs = [idx_lo, idx_hi, idx_hi + 1]
    else:
        idxs = [idx_lo, idx_hi]

    x = abs_deltas[idxs]
    y = ivs[idxs]
    coeffs = np.polyfit(x, y, deg=1)
    iv_interp = float(np.polyval(coeffs, target_delta))
    if not (min(y) * 0.80 <= iv_interp <= max(y) * 1.20):
        return np.nan
    return iv_interp


def interpolate_25delta_skew(
    chain_df: pd.DataFrame,
    target_delta: float = 0.25,
    delta_range: tuple = (0.10, 0.50),
) -> pd.DataFrame:
    """Compute 25-delta skew as PE IV minus CE IV for each timestamp."""
    required = ["timestamp", "option_type", "strike", "iv", "delta"]
    missing = [col for col in required if col not in chain_df.columns]
    if missing:
        raise ValueError(f"chain_df missing required columns: {missing}")

    valid = chain_df[chain_df["iv"].notna() & chain_df["delta"].notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=["timestamp", "iv_25d_CE", "iv_25d_PE", "skew_25d"])

    pe_rows = []
    ce_rows = []

    for ts, group in valid.groupby("timestamp"):
        ce_group = group[group["option_type"] == "CE"]
        pe_group = group[group["option_type"] == "PE"]
        if not ce_group.empty:
            ce_rows.append({"timestamp": ts, "iv_25d_CE": _interp_single_iv(ce_group, target_delta, delta_range)})
        if not pe_group.empty:
            pe_rows.append({"timestamp": ts, "iv_25d_PE": _interp_single_iv(pe_group, target_delta, delta_range)})

    ce_df = pd.DataFrame(ce_rows)
    pe_df = pd.DataFrame(pe_rows)
    result = ce_df.merge(pe_df, on="timestamp", how="outer")
    result["skew_25d"] = result["iv_25d_PE"] - result["iv_25d_CE"]
    result = result.sort_values("timestamp").reset_index(drop=True)
    return result


def validate_skew(skew_df: pd.DataFrame, spike_threshold: float = 0.05) -> dict:
    """Validate skew range and spike behavior without printing or mutating the input."""
    required = ["timestamp", "skew_25d"]
    missing = [col for col in required if col not in skew_df.columns]
    if missing:
        raise ValueError(f"skew_df missing required columns: {missing}")

    valid = skew_df[skew_df["skew_25d"].notna()].copy()
    if valid.empty:
        return {
            "skew_range": {"min": None, "max": None, "mean": None, "median": None},
            "negative_skew_count": 0,
            "elevated_skew_count": 0,
            "extreme_skew_count": 0,
            "spikes": {
                "count": 0,
                "threshold": spike_threshold,
                "session_open": [],
                "intraday": [],
            },
        }

    valid = valid.sort_values("timestamp").reset_index(drop=True)
    valid["skew_chg"] = valid["skew_25d"].diff().abs()
    spikes = valid[valid["skew_chg"] > spike_threshold].copy()

    valid["date"] = valid["timestamp"].dt.date
    first_bars = valid.groupby("date")["timestamp"].min()
    session_open_ts = spikes[spikes["timestamp"].isin(first_bars.values)]
    intraday_ts = spikes[~spikes["timestamp"].isin(first_bars.values)]

    return {
        "skew_range": {
            "min": float(valid["skew_25d"].min()),
            "max": float(valid["skew_25d"].max()),
            "mean": float(valid["skew_25d"].mean()),
            "median": float(valid["skew_25d"].median()),
        },
        "negative_skew_count": int((valid["skew_25d"] < 0).sum()),
        "elevated_skew_count": int((valid["skew_25d"] > 0.15).sum()),
        "extreme_skew_count": int((valid["skew_25d"] > 0.25).sum()),
        "spikes": {
            "count": int(len(spikes)),
            "threshold": spike_threshold,
            "session_open": session_open_ts["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
            "intraday": intraday_ts["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
            "session_open_count": int(len(session_open_ts)),
            "intraday_count": int(len(intraday_ts)),
        },
    }
