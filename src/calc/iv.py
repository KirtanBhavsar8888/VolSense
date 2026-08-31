from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm


def _normalize_flag(flag: object) -> float:
    if isinstance(flag, str):
        value = flag.lower()
        return 1.0 if value in {"c", "call", "ce"} else -1.0
    return 1.0 if float(flag) > 0 else -1.0


def bs_price(F: float, K: float, T: float, r: float, sigma: float, flag: object) -> float:
    """European Black-Scholes price using forward F as the underlying."""
    if T <= 0 or sigma <= 0:
        return np.nan
    flag_value = _normalize_flag(flag)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if flag_value == 1.0:
        return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def bs_delta(F: float, K: float, T: float, r: float, sigma: float, flag: object) -> float:
    """Forward delta dV/dF for a European option."""
    if T <= 0 or sigma <= 0 or np.isnan(sigma):
        return np.nan
    flag_value = _normalize_flag(flag)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    if flag_value == 1.0:
        return float(norm.cdf(d1))
    return float(norm.cdf(d1) - 1.0)


def compute_iv(ltp: float, F: float, K: float, T: float, r: float, flag: object, tol: float = 1e-6) -> float:
    """Implied volatility via Brent root-finding, returning NaN on any failure."""
    if not np.isfinite(ltp) or not np.isfinite(F) or not np.isfinite(K) or not np.isfinite(T):
        return np.nan
    if T <= 0 or ltp <= 0 or F <= 0 or K <= 0:
        return np.nan

    flag_value = _normalize_flag(flag)
    intrinsic = max(np.exp(-r * T) * (F - K if flag_value == 1.0 else K - F), 0.0)
    if ltp < intrinsic - tol:
        return np.nan

    try:
        obj = lambda sigma: bs_price(F, K, T, r, sigma, flag_value) - ltp
        lo, hi = 1e-4, 10.0
        f_lo, f_hi = obj(lo), obj(hi)
        if not np.isfinite(f_lo) or not np.isfinite(f_hi):
            return np.nan
        if f_lo * f_hi > 0:
            return np.nan
        return brentq(obj, lo, hi, xtol=tol, maxiter=300)
    except Exception:
        return np.nan


def vectorized_iv(
    ltp,
    F,
    K,
    T,
    r: float,
    flag,
    n_iter: int = 50,
):
    """Vectorized Newton-Raphson implied-vol solver across arrays."""
    ltp = np.asarray(ltp, dtype=float)
    F = np.asarray(F, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    flag_arr = np.asarray([_normalize_flag(v) for v in flag], dtype=float)

    valid = (
        np.isfinite(ltp)
        & np.isfinite(F)
        & np.isfinite(K)
        & np.isfinite(T)
        & (ltp > 0)
        & (F > 0)
        & (K > 0)
        & (T > 0)
    )

    sigma = np.full_like(ltp, np.nan, dtype=float)
    if not valid.any():
        return sigma

    sigma[valid] = np.sqrt(2 * np.pi / T[valid]) * ltp[valid] / F[valid]
    sigma[valid] = np.clip(sigma[valid], 1e-4, 5.0)

    for _ in range(n_iter):
        d1 = (np.log(F[valid] / K[valid]) + 0.5 * sigma[valid] ** 2 * T[valid]) / (sigma[valid] * np.sqrt(T[valid]))
        d2 = d1 - sigma[valid] * np.sqrt(T[valid])
        price = np.exp(-r * T[valid]) * (
            flag_arr[valid] * (F[valid] * norm.cdf(flag_arr[valid] * d1) - K[valid] * norm.cdf(flag_arr[valid] * d2))
        )
        vega = F[valid] * np.exp(-r * T[valid]) * norm.pdf(d1) * np.sqrt(T[valid])
        vega = np.where(vega < 1e-10, 1e-10, vega)
        diff = price - ltp[valid]
        sigma[valid] = sigma[valid] - diff / vega
        sigma[valid] = np.clip(sigma[valid], 1e-4, 10.0)

    d1 = (np.log(F[valid] / K[valid]) + 0.5 * sigma[valid] ** 2 * T[valid]) / (sigma[valid] * np.sqrt(T[valid]))
    d2 = d1 - sigma[valid] * np.sqrt(T[valid])
    final_price = np.exp(-r * T[valid]) * (
        flag_arr[valid] * (F[valid] * norm.cdf(flag_arr[valid] * d1) - K[valid] * norm.cdf(flag_arr[valid] * d2))
    )
    bad = np.abs(final_price - ltp[valid]) > 0.5
    sigma[valid] = np.where(bad, np.nan, sigma[valid])
    return sigma


def vectorized_delta(F, K, T, r, sigma, flag):
    """Vectorized Black-Scholes forward delta using the corrected call/put formula."""
    F = np.asarray(F, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    flag_arr = np.asarray([_normalize_flag(v) for v in flag], dtype=float)

    valid = np.isfinite(F) & np.isfinite(K) & np.isfinite(T) & np.isfinite(sigma) & (T > 0) & (sigma > 0)
    delta = np.full_like(F, np.nan, dtype=float)
    if not valid.any():
        return delta

    d1 = np.full_like(F, np.nan, dtype=float)
    d1[valid] = (
        np.log(F[valid] / K[valid]) + 0.5 * sigma[valid] ** 2 * T[valid]
    ) / (sigma[valid] * np.sqrt(T[valid]))

    call_mask = valid & (flag_arr == 1.0)
    put_mask = valid & (flag_arr == -1.0)
    delta[call_mask] = norm.cdf(d1[call_mask])
    delta[put_mask] = norm.cdf(d1[put_mask]) - 1.0
    return delta


def compute_iv_delta(chain_df: pd.DataFrame, futures_df: pd.DataFrame, risk_free_rate: float) -> pd.DataFrame:
    """Compute raw IV and delta columns for the option chain using a synthetic future series."""
    required_chain = ["timestamp", "strike", "option_type", "ltp", "illiquid", "dte"]
    missing_chain = [col for col in required_chain if col not in chain_df.columns]
    if missing_chain:
        raise ValueError(f"chain_df missing required columns: {missing_chain}")

    required_futures = ["timestamp", "synth_future"]
    missing_futures = [col for col in required_futures if col not in futures_df.columns]
    if missing_futures:
        raise ValueError(f"futures_df missing required columns: {missing_futures}")

    work = chain_df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    work["option_type"] = work["option_type"].astype(str).str.upper()
    work = work.merge(futures_df[["timestamp", "synth_future"]], on="timestamp", how="left")

    work = work[
        (~work["illiquid"].fillna(False))
        & work["synth_future"].notna()
        & (work["ltp"].notna())
        & (work["ltp"] > 0)
    ].copy()

    if work.empty:
        work["iv"] = np.nan
        work["delta"] = np.nan
        return work

    work["T_adj"] = (work["dte"].clip(lower=0.5) / 365.0)
    work["flag"] = np.where(work["option_type"] == "CE", 1.0, -1.0)

    ltp_arr = work["ltp"].astype(float).to_numpy()
    F_arr = work["synth_future"].astype(float).to_numpy()
    K_arr = work["strike"].astype(float).to_numpy()
    T_arr = work["T_adj"].astype(float).to_numpy()
    flag_arr = work["flag"].astype(float).to_numpy()

    intrinsic = np.exp(-risk_free_rate * T_arr) * np.maximum(flag_arr * (F_arr - K_arr), 0.0)
    ltp_arr[ltp_arr < (intrinsic - 0.5)] = np.nan

    ivs = vectorized_iv(ltp_arr, F_arr, K_arr, T_arr, risk_free_rate, flag_arr)
    deltas = vectorized_delta(F_arr, K_arr, T_arr, risk_free_rate, ivs, flag_arr)

    work["iv"] = ivs
    work["delta"] = deltas

    # Original notebook bad IV flag used for reference only:
    # bad_iv_mask = (df_near['iv'] < 0.005) & (df_near['delta'].abs() > 0.95)
    return work


def validate_iv_delta(df: pd.DataFrame) -> dict:
    """Validate IV and delta ranges and monotonicity; no mutation, no printing."""
    required = ["timestamp", "option_type", "strike", "iv", "delta"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"df missing required columns: {missing}")

    valid = df[df["iv"].notna() & df["delta"].notna()].copy()
    call = valid[valid["option_type"] == "CE"]
    put = valid[valid["option_type"] == "PE"]

    bad_iv_mask = (valid["iv"] < 0.005) & (valid["delta"].abs() > 0.95)
    bad_iv_rows = valid.loc[bad_iv_mask, ["timestamp", "strike", "option_type", "iv", "delta"]].copy()

    iv_range = {
        "min": float(valid["iv"].min()) if not valid.empty else None,
        "max": float(valid["iv"].max()) if not valid.empty else None,
    }
    call_delta_range = {
        "min": float(call["delta"].min()) if not call.empty else None,
        "max": float(call["delta"].max()) if not call.empty else None,
    }
    put_delta_range = {
        "min": float(put["delta"].min()) if not put.empty else None,
        "max": float(put["delta"].max()) if not put.empty else None,
    }

    iv_low_count = int((valid["iv"] < 0.02).sum()) if not valid.empty else 0
    iv_high_count = int((valid["iv"] > 2.0).sum()) if not valid.empty else 0
    delta_out_of_bounds = int(((valid["delta"] < -1.0) | (valid["delta"] > 1.0)).sum()) if not valid.empty else 0

    monotonicity_pass = 0
    monotonicity_fail = 0
    offending_rows = []
    for ts, group in call.groupby("timestamp"):
        sub = group.sort_values("strike").copy()
        if len(sub) < 2:
            monotonicity_pass += 1
            continue
        if (sub["delta"].diff().dropna() <= 0).all():
            monotonicity_pass += 1
        else:
            monotonicity_fail += 1
            offending_rows.append(
                {
                    "timestamp": ts,
                    "n_rows": int(len(sub)),
                    "delta_sequence": sub["delta"].tolist(),
                }
            )

    return {
        "iv_range": iv_range,
        "call_delta_range": call_delta_range,
        "put_delta_range": put_delta_range,
        "iv_low_count": iv_low_count,
        "iv_high_count": iv_high_count,
        "delta_out_of_bounds": delta_out_of_bounds,
        "bad_iv_mask": {
            "count": int(len(bad_iv_rows)),
            "rows": bad_iv_rows.to_dict(orient="records"),
        },
        "monotonicity": {
            "pass_count": monotonicity_pass,
            "fail_count": monotonicity_fail,
            "offending_rows": offending_rows,
        },
    }
