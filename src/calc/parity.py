from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_PARITY_COLUMNS = [
    "timestamp",
    "expiry",
    "strike",
    "option_type",
    "ltp",
    "illiquid",
]


def synthetic_future(
    chain_df: pd.DataFrame,
    risk_free_rate: float = 0.065,
    outlier_pct: float = 1.0,
) -> pd.DataFrame:
    """Build per-timestamp synthetic futures using put-call parity and outlier filtering."""
    if not isinstance(chain_df, pd.DataFrame):
        raise TypeError("chain_df must be a pandas DataFrame")

    missing = [col for col in REQUIRED_PARITY_COLUMNS if col not in chain_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if not np.isfinite(risk_free_rate):
        raise ValueError("risk_free_rate must be finite")

    df = chain_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["option_type"] = df["option_type"].astype(str).str.upper()

    df["dte"] = (df["expiry"] - df["timestamp"].dt.normalize()).dt.days
    df["T"] = df["dte"] / 365.0

    liquid = df[~df["illiquid"].fillna(False)].copy()
    liquid = liquid[liquid["ltp"].notna() & (liquid["ltp"] > 0)].copy()
    if liquid.empty:
        raise ValueError("No liquid rows remain after filtering")

    pivot = liquid.pivot_table(
        index=["timestamp", "expiry", "strike", "dte", "T"],
        columns="option_type",
        values="ltp",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.dropna(subset=["CE", "PE"]).copy()
    if pivot.empty:
        raise ValueError("No valid CE/PE pairs remain for parity computation")

    pivot["synth_F"] = (pivot["CE"] - pivot["PE"]) * np.exp(risk_free_rate * pivot["T"]) + pivot["strike"]
    pivot["synth_median_ts"] = pivot.groupby("timestamp")["synth_F"].transform("median")
    pivot["synth_dev_pct"] = (
        ((pivot["synth_F"] - pivot["synth_median_ts"]) / pivot["synth_median_ts"]) * 100
    ).abs()

    outliers = pivot[pivot["synth_dev_pct"] > outlier_pct].copy()
    pivot_clean = pivot[pivot["synth_dev_pct"] <= outlier_pct].copy()
    if pivot_clean.empty:
        raise ValueError("All parity pairs were excluded as outliers")

    consensus = (
        pivot_clean.groupby("timestamp")
        .agg(
            synth_future=("synth_F", "median"),
            n_strikes_used=("synth_F", "count"),
            synth_q25=("synth_F", lambda x: x.quantile(0.25)),
            synth_q75=("synth_F", lambda x: x.quantile(0.75)),
            dte=("dte", "first"),
        )
        .reset_index()
    )
    consensus["outliers_excluded"] = consensus["timestamp"].map(
        pivot.groupby("timestamp")["synth_dev_pct"].apply(lambda s: int((s > outlier_pct).sum()))
    )
    consensus["iqr"] = consensus["synth_q75"] - consensus["synth_q25"]
    consensus["synth_pct_chg"] = consensus["synth_future"].pct_change().fillna(0.0) * 100.0

    consensus = consensus.sort_values("timestamp").reset_index(drop=True)
    if (consensus["synth_future"] <= 0).any():
        raise ValueError("Synthetic future values must remain positive")

    return consensus
