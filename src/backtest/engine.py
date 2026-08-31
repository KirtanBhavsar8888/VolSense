"""Generalized strategy backtest engine for NIFTY option chains.

Reuses the existing calc layer (parity, iv, skew) — does NOT reimplement
IV/delta/parity math.  Supports exactly 3 strategy types for v1:

1. ATM Straddle  – long/short 1 CE + 1 PE at the strike nearest the
   synthetic future at entry time.
2. OTM Strangle  – long/short 1 CE + 1 PE, each at a specified target
   delta (default 0.25), using nearest-strike selection.
3. Single-leg    – one CE or PE, at ATM / ITM (N strikes ITM) /
   OTM (N strikes OTM), long or short.

Uses ONLY real NIFTY chain data — no synthetic/random data generation.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.calc.iv import compute_iv_delta
from src.calc.parity import synthetic_future


# ---------------------------------------------------------------------------
# Strike-selection helpers (generalised from interpolate_25delta_skew)
# ---------------------------------------------------------------------------

def _nearest_strike(strikes: np.ndarray, target: float) -> float:
    """Return the strike closest to *target*."""
    idx = int(np.argmin(np.abs(strikes - target)))
    return float(strikes[idx])


def _strike_for_delta(
    iv_delta_df: pd.DataFrame,
    timestamp: pd.Timestamp,
    option_type: str,
    target_delta: float,
) -> float | None:
    """Select the strike whose |delta| is closest to *target_delta* at *timestamp*.

    Generalises the nearest-strike selection logic used in
    ``interpolate_25delta_skew``.
    """
    subset = iv_delta_df[
        (iv_delta_df["timestamp"] == timestamp)
        & (iv_delta_df["option_type"] == option_type)
        & iv_delta_df["iv"].notna()
        & iv_delta_df["delta"].notna()
    ].copy()
    if subset.empty:
        return None
    subset["abs_delta"] = subset["delta"].abs()
    idx = int(np.argmin(np.abs(subset["abs_delta"].values - target_delta)))
    return float(subset.iloc[idx]["strike"])


def _strike_for_moneyness(
    chain_df: pd.DataFrame,
    timestamp: pd.Timestamp,
    synth_future: float,
    option_type: str,
    offset: int,
) -> float | None:
    """Select strike at *offset* from ATM.

    - offset = 0  → ATM
    - offset > 0  → OTM (CE: higher strike, PE: lower strike)
    - offset < 0  → ITM (CE: lower strike, PE: higher strike)
    """
    subset = chain_df[
        (chain_df["timestamp"] == timestamp)
        & (chain_df["option_type"] == option_type)
        & chain_df["ltp"].notna()
        & (~chain_df["illiquid"].fillna(False))
    ].copy()
    if subset.empty:
        return None
    strikes = np.sort(subset["strike"].values)
    atm_strike = _nearest_strike(strikes, synth_future)

    if option_type == "CE":
        # CE: ATM is nearest; OTM means higher strike, ITM means lower
        idx = int(np.searchsorted(strikes, atm_strike)) - offset
    else:
        # PE: ATM is nearest; OTM means lower strike, ITM means higher
        idx = int(np.searchsorted(strikes, atm_strike)) + offset

    idx = max(0, min(idx, len(strikes) - 1))
    return float(strikes[idx])


# ---------------------------------------------------------------------------
# Leg pricing helpers
# ---------------------------------------------------------------------------

def _get_option_price(
    chain_df: pd.DataFrame,
    timestamp: pd.Timestamp,
    strike: float,
    option_type: str,
) -> float | None:
    """Return the LTP for a specific option at a specific timestamp."""
    row = chain_df[
        (chain_df["timestamp"] == timestamp)
        & (chain_df["strike"] == strike)
        & (chain_df["option_type"] == option_type)
    ]
    if row.empty:
        return None
    val = row.iloc[0]["ltp"]
    return float(val) if pd.notna(val) else None


def _get_option_price_at_or_before(
    chain_df: pd.DataFrame,
    timestamp: pd.Timestamp,
    strike: float,
    option_type: str,
) -> float | None:
    """Return LTP at *timestamp*, or fall back to the most recent earlier bar."""
    price = _get_option_price(chain_df, timestamp, strike, option_type)
    if price is not None:
        return price
    earlier = chain_df[
        (chain_df["timestamp"] <= timestamp)
        & (chain_df["strike"] == strike)
        & (chain_df["option_type"] == option_type)
    ].sort_values("timestamp", ascending=False)
    if earlier.empty:
        return None
    val = earlier.iloc[0]["ltp"]
    return float(val) if pd.notna(val) else None


# ---------------------------------------------------------------------------
# Strategy builders
# ---------------------------------------------------------------------------

def _build_atm_straddle(
    chain_df: pd.DataFrame,
    iv_delta_df: pd.DataFrame | None,
    futures_df: pd.DataFrame,
    entry_time: pd.Timestamp,
    strategy: dict,
) -> list[dict[str, Any]]:
    """Build legs for an ATM straddle: 1 CE + 1 PE at the nearest strike to synth future."""
    ts = entry_time
    fut_row = futures_df[futures_df["timestamp"] == ts]
    if fut_row.empty:
        # Use the closest earlier timestamp
        fut_row = futures_df[futures_df["timestamp"] <= ts].sort_values("timestamp", ascending=False)
    if fut_row.empty:
        raise ValueError(f"No synthetic future available at or before {ts}")
    synth_f = float(fut_row.iloc[0]["synth_future"])

    strikes = chain_df[
        (chain_df["timestamp"] == ts)
        & (~chain_df["illiquid"].fillna(False))
    ]["strike"].unique()
    if len(strikes) == 0:
        raise ValueError(f"No liquid strikes at {ts}")
    strike = _nearest_strike(np.array(strikes), synth_f)

    qty = strategy.get("quantity", 1)
    direction = strategy.get("direction", "long")
    return [
        {"option_type": "CE", "strike": strike, "quantity": qty, "direction": direction},
        {"option_type": "PE", "strike": strike, "quantity": qty, "direction": direction},
    ]


def _build_otm_strangle(
    chain_df: pd.DataFrame,
    iv_delta_df: pd.DataFrame | None,
    futures_df: pd.DataFrame,
    entry_time: pd.Timestamp,
    strategy: dict,
) -> list[dict[str, Any]]:
    """Build legs for an OTM strangle: 1 CE + 1 PE at target delta."""
    ts = entry_time
    target_delta = strategy.get("target_delta", 0.25)
    qty = strategy.get("quantity", 1)
    direction = strategy.get("direction", "long")

    if iv_delta_df is None or iv_delta_df.empty:
        raise ValueError("iv_delta_df required for OTM strangle strategy")

    ce_strike = _strike_for_delta(iv_delta_df, ts, "CE", target_delta)
    pe_strike = _strike_for_delta(iv_delta_df, ts, "PE", target_delta)

    if ce_strike is None or pe_strike is None:
        raise ValueError(f"Could not find strikes for delta {target_delta} at {ts}")

    return [
        {"option_type": "CE", "strike": ce_strike, "quantity": qty, "direction": direction},
        {"option_type": "PE", "strike": pe_strike, "quantity": qty, "direction": direction},
    ]


def _build_single_leg(
    chain_df: pd.DataFrame,
    iv_delta_df: pd.DataFrame | None,
    futures_df: pd.DataFrame,
    entry_time: pd.Timestamp,
    strategy: dict,
) -> list[dict[str, Any]]:
    """Build a single-leg option."""
    ts = entry_time
    option_type = strategy.get("option_type", "CE")
    moneyness = strategy.get("moneyness", "ATM")
    offset = strategy.get("offset", 0)
    qty = strategy.get("quantity", 1)
    direction = strategy.get("direction", "long")

    fut_row = futures_df[futures_df["timestamp"] == ts]
    if fut_row.empty:
        fut_row = futures_df[futures_df["timestamp"] <= ts].sort_values("timestamp", ascending=False)
    if fut_row.empty:
        raise ValueError(f"No synthetic future available at or before {ts}")
    synth_f = float(fut_row.iloc[0]["synth_future"])

    if moneyness == "ATM":
        strike_offset = 0
    elif moneyness == "OTM":
        strike_offset = abs(offset) if offset != 0 else 1
    elif moneyness == "ITM":
        strike_offset = -abs(offset) if offset != 0 else -1
    else:
        raise ValueError(f"Unknown moneyness: {moneyness}")

    strike = _strike_for_moneyness(chain_df, ts, synth_f, option_type, strike_offset)
    if strike is None:
        raise ValueError(f"Could not find strike for {moneyness} {option_type} at {ts}")

    return [
        {"option_type": option_type, "strike": strike, "quantity": qty, "direction": direction},
    ]


def _build_custom(
    chain_df: pd.DataFrame,
    iv_delta_df: pd.DataFrame | None,
    futures_df: pd.DataFrame,
    entry_time: pd.Timestamp,
    strategy: dict,
) -> list[dict[str, Any]]:
    """Build an arbitrary multi-leg strategy from explicit leg definitions.

    strategy must contain a "legs" list, each entry being:
        {"option_type": "CE"|"PE", "moneyness": "ATM"|"ITM"|"OTM",
         "offset": int, "direction": "long"|"short", "quantity": int}
    """
    ts = entry_time
    legs_def = strategy.get("legs", [])
    if not legs_def:
        raise ValueError("Custom strategy requires a non-empty 'legs' list")

    # Resolve synthetic future once for all ATM strike selections
    fut_row = futures_df[futures_df["timestamp"] == ts]
    if fut_row.empty:
        fut_row = futures_df[futures_df["timestamp"] <= ts].sort_values(
            "timestamp", ascending=False
        )
    if fut_row.empty:
        raise ValueError(f"No synthetic future available at or before {ts}")
    synth_f = float(fut_row.iloc[0]["synth_future"])

    resolved: list[dict[str, Any]] = []
    for leg_def in legs_def:
        ot = leg_def.get("option_type", "CE")
        moneyness = leg_def.get("moneyness", "ATM")
        offset = leg_def.get("offset", 0)
        qty = leg_def.get("quantity", 1)
        direction = leg_def.get("direction", "long")

        if moneyness == "ATM":
            strike_off = 0
        elif moneyness == "OTM":
            strike_off = abs(offset) if offset != 0 else 1
        elif moneyness == "ITM":
            strike_off = -abs(offset) if offset != 0 else -1
        else:
            raise ValueError(f"Unknown moneyness: {moneyness}")

        strike = _strike_for_moneyness(chain_df, ts, synth_f, ot, strike_off)
        if strike is None:
            raise ValueError(
                f"Could not find strike for {moneyness} {ot} at {ts}"
            )
        resolved.append(
            {"option_type": ot, "strike": strike, "quantity": qty, "direction": direction}
        )
    return resolved


STRATEGY_BUILDERS = {
    "atm_straddle": _build_atm_straddle,
    "otm_strangle": _build_otm_strangle,
    "single_leg": _build_single_leg,
    "custom": _build_custom,
}


# ---------------------------------------------------------------------------
# Exit logic (generalised from notebook Section 8)
# ---------------------------------------------------------------------------

def _evaluate_exit(
    legs: list[dict[str, Any]],
    entry_prices: list[float],
    current_prices: list[float],
    exit_rule: dict,
    hold_minutes: float,
) -> tuple[bool, str]:
    """Check SL / TP / max-hold for the combined position.

    Returns (should_exit, reason).
    """
    stop_loss_pct = exit_rule.get("stop_loss_pct", 5.0)
    take_profit_pct = exit_rule.get("take_profit_pct", 10.0)
    max_hold_minutes = exit_rule.get("max_hold_minutes", 375)  # 6.25 hours

    total_entry = 0.0
    total_current = 0.0
    for leg, ep, cp in zip(legs, entry_prices, current_prices):
        sign = 1.0 if leg["direction"] == "long" else -1.0
        total_entry += sign * ep * leg["quantity"]
        total_current += sign * cp * leg["quantity"]

    if total_entry == 0:
        return False, ""

    pnl_pct = ((total_current - total_entry) / abs(total_entry)) * 100.0

    if pnl_pct <= -stop_loss_pct:
        return True, "stop_loss"
    if pnl_pct >= take_profit_pct:
        return True, "take_profit"
    if hold_minutes >= max_hold_minutes:
        return True, "max_hold"
    return False, ""


# ---------------------------------------------------------------------------
# Entry Greeks helper
# ---------------------------------------------------------------------------

def _get_entry_greeks(
    iv_delta_df: pd.DataFrame,
    legs: list[dict[str, Any]],
    entry_ts: pd.Timestamp,
) -> dict[str, Any]:
    """Capture entry_iv and entry_delta for each leg from iv_delta_df.

    Returns {"legs": [{"iv": ..., "delta": ...}, ...], "net_delta": ...}.
    """
    leg_greeks: list[dict[str, Any]] = []
    net_delta = 0.0

    for leg in legs:
        row = iv_delta_df[
            (iv_delta_df["timestamp"] == entry_ts)
            & (iv_delta_df["option_type"] == leg["option_type"])
            & (iv_delta_df["strike"].astype(float) == leg["strike"])
            & iv_delta_df["iv"].notna()
            & iv_delta_df["delta"].notna()
        ]
        if row.empty:
            leg_greeks.append({"iv": None, "delta": None})
        else:
            iv_val = float(row.iloc[0]["iv"])
            delta_val = float(row.iloc[0]["delta"])
            leg_greeks.append({"iv": iv_val, "delta": delta_val})
            direction_sign = 1.0 if leg["direction"] == "long" else -1.0
            net_delta += delta_val * direction_sign * leg["quantity"]

    return {"legs": leg_greeks, "net_delta": round(net_delta, 6)}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_backtest(
    chain_df: pd.DataFrame,
    strategy: dict,
    entry_time: str,
    exit_rule: dict,
    lot_size: int | None = None,
    num_lots: int = 1,
) -> dict[str, Any]:
    """Run a backtest for the given strategy on real chain data.

    Parameters
    ----------
    chain_df : DataFrame with columns [timestamp, expiry, strike, option_type, ltp, illiquid]
    strategy : dict with keys:
        - type: "atm_straddle" | "otm_strangle" | "single_leg"
        - direction: "long" | "short"
        - quantity: int (default 1)
        - target_delta: float (for otm_strangle, default 0.25)
        - option_type: "CE" | "PE" (for single_leg)
        - moneyness: "ATM" | "ITM" | "OTM" (for single_leg)
        - offset: int (for single_leg, default 0)
    entry_time : str timestamp for entry
    exit_rule : dict with keys:
        - stop_loss_pct: float (default 5.0)
        - take_profit_pct: float (default 10.0)
        - max_hold_minutes: float (default 375)
    lot_size : int or None — exchange-mandated lot size. Required for
        lot-scaled P&L. If None, pnl_per_unit is returned but pnl is
        set to None (caller must supply lot_size for scaled figures).
    num_lots : int, default 1 — number of lots traded.

    Returns
    -------
    dict with keys: entry_price, exit_price, exit_reason, pnl_per_unit,
        pnl_pct, pnl (lot-scaled, None if lot_size not provided), greeks,
        legs, trade_log
    """
    # --- Validate inputs ---
    strategy_type = strategy.get("type")
    if strategy_type not in STRATEGY_BUILDERS:
        raise ValueError(f"Unknown strategy type: {strategy_type}. Must be one of {list(STRATEGY_BUILDERS)}")

    required_cols = ["timestamp", "expiry", "strike", "option_type", "ltp", "illiquid"]
    missing = [c for c in required_cols if c not in chain_df.columns]
    if missing:
        raise ValueError(f"chain_df missing required columns: {missing}")

    # --- Prepare data ---
    df = chain_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["option_type"] = df["option_type"].astype(str).str.upper()
    df["strike"] = df["strike"].astype(float)
    df["ltp"] = df["ltp"].astype(float)

    entry_ts = pd.to_datetime(entry_time)

    # Build synthetic futures and IV/delta for the session
    futures_df = synthetic_future(df)
    iv_delta_df = compute_iv_delta(df, futures_df, risk_free_rate=0.065)

    # --- Build strategy legs ---
    builder = STRATEGY_BUILDERS[strategy_type]
    legs = builder(df, iv_delta_df, futures_df, entry_ts, strategy)

    # --- Get entry prices ---
    entry_prices: list[float] = []
    for leg in legs:
        price = _get_option_price(df, entry_ts, leg["strike"], leg["option_type"])
        if price is None:
            raise ValueError(
                f"No price for {leg['option_type']} K={leg['strike']} at {entry_ts}"
            )
        entry_prices.append(price)

    total_entry_cost = sum(
        (1.0 if leg["direction"] == "long" else -1.0) * ep * leg["quantity"]
        for leg, ep in zip(legs, entry_prices)
    )

    # --- Entry Greeks ---
    greeks = _get_entry_greeks(iv_delta_df, legs, entry_ts)

    # --- Walk forward through timestamps ---
    timestamps = sorted(df["timestamp"].unique())
    entry_idx = 0
    for i, ts in enumerate(timestamps):
        if ts >= entry_ts:
            entry_idx = i
            break

    trade_log: list[dict[str, Any]] = []
    hold_minutes = 0.0
    exit_reason = ""
    exit_price_total = 0.0

    for i in range(entry_idx, len(timestamps)):
        ts = timestamps[i]
        dt_minutes = 0.0
        if i > entry_idx:
            dt_minutes = (ts - timestamps[i - 1]).total_seconds() / 60.0
        hold_minutes += dt_minutes

        current_prices: list[float] = []
        for leg in legs:
            p = _get_option_price_at_or_before(df, ts, leg["strike"], leg["option_type"])
            if p is None:
                p = entry_prices[legs.index(leg)]  # fallback to entry price
            current_prices.append(p)

        should_exit, reason = _evaluate_exit(legs, entry_prices, current_prices, exit_rule, hold_minutes)

        log_entry = {
            "timestamp": ts.isoformat(),
            "prices": {
                leg["option_type"] + "_K" + str(int(leg["strike"])): cp
                for leg, cp in zip(legs, current_prices)
            },
            "hold_minutes": round(hold_minutes, 1),
        }
        trade_log.append(log_entry)

        if should_exit:
            exit_reason = reason
            exit_price_total = sum(
                (1.0 if leg["direction"] == "long" else -1.0) * cp * leg["quantity"]
                for leg, cp in zip(legs, current_prices)
            )
            break
    else:
        # Reached end of data without exiting — use last prices
        if trade_log:
            last = trade_log[-1]
            exit_price_total = sum(
                (1.0 if leg["direction"] == "long" else -1.0) * last["prices"].get(
                    leg["option_type"] + "_K" + str(int(leg["strike"])), entry_prices[i]
                ) * leg["quantity"]
                for i, leg in enumerate(legs)
            )
        exit_reason = "end_of_data"

    pnl_per_unit = exit_price_total - total_entry_cost
    pnl_pct = (pnl_per_unit / abs(total_entry_cost) * 100.0) if total_entry_cost != 0 else 0.0

    # Lot-scaled P&L
    if lot_size is not None:
        pnl = round(pnl_per_unit * lot_size * num_lots, 2)
    else:
        pnl = None

    return {
        "strategy": strategy,
        "entry_time": entry_ts.isoformat(),
        "entry_price": round(total_entry_cost, 2),
        "exit_price": round(exit_price_total, 2),
        "exit_reason": exit_reason,
        "pnl_per_unit": round(pnl_per_unit, 2),
        "pnl_pct": round(pnl_pct, 2),
        "pnl": pnl,
        "greeks": greeks,
        "legs": legs,
        "trade_log": trade_log,
    }
