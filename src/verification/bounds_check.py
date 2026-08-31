from __future__ import annotations

from typing import Any

import pandas as pd


def check_no_arbitrage_bounds(
    chain_df: pd.DataFrame,
    price_ceiling: float | None = None,
    price_scale: float = 10.0,
) -> dict[str, Any]:
    """Flag option chain rows that violate basic no-arbitrage conditions or look near-expiry unstable.
    
    Args:
        chain_df: Option chain DataFrame
        price_ceiling: Max absolute price for near-expiry rows (default 50000 for India INR scale)
        price_scale: Multiplier for max price relative to strike (default 10.0)
    """
    if chain_df is None:
        return {"ok": False, "issues": ["chain_df is None"], "counts": {}}

    df = chain_df.copy()
    required = {"timestamp", "expiry", "strike", "option_type", "ltp", "illiquid", "dte"}
    missing = sorted(required - set(df.columns))
    if missing:
        return {"ok": False, "issues": [f"Missing required columns: {missing}"], "counts": {}}

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["option_type"] = df["option_type"].astype(str).str.upper()
    df["ltp"] = pd.to_numeric(df["ltp"], errors="coerce")
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    df["dte"] = pd.to_numeric(df["dte"], errors="coerce")

    # Set default price_ceiling if not provided (INR scale default)
    if price_ceiling is None:
        price_ceiling = 50000.0

    issues: list[str] = []
    bad_rows_by_reason: dict[str, list[dict[str, Any]]] = {
        "non_finite": [],
        "near_expiry": [],
        "illiquid": [],
        "absurd_price": [],
        "dte_mismatch": [],
        "bad_option_type": [],
    }

    # Basic sanity: positive price, strike, and finite DTE.
    finite_mask = df["ltp"].notna() & df["strike"].notna() & df["dte"].notna()
    non_finite = int((~finite_mask).sum())
    if non_finite:
        issues.append(f"Non-finite price/strike/DTE rows: {non_finite}")
        non_finite_rows = df[~finite_mask].copy()
        for _, row in non_finite_rows.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "non_finite"
            bad_rows_by_reason["non_finite"].append(row_dict)

    # Validate option_type is only CE or PE.
    valid_types = {"CE", "PE"}
    bad_types = df[~df["option_type"].isin(valid_types)].copy()
    if not bad_types.empty:
        bad_type_count = int(bad_types.shape[0])
        issues.append(f"Invalid option_type rows: {bad_type_count}")
        for _, row in bad_types.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "bad_option_type"
            bad_rows_by_reason["bad_option_type"].append(row_dict)

    # DTE consistency check: dte should match (expiry - timestamp.normalize()).dt.days ±1.
    # This matches parity.py's DTE calculation exactly.
    df["dte_computed"] = (df["expiry"] - df["timestamp"].dt.normalize()).dt.days
    dte_mismatch = df[
        (df["dte"].notna()) & (df["dte_computed"].notna()) & 
        ((df["dte"] - df["dte_computed"]).abs() > 1)
    ].copy()
    if not dte_mismatch.empty:
        dte_mismatch_count = int(dte_mismatch.shape[0])
        issues.append(f"DTE/expiry mismatch rows: {dte_mismatch_count}")
        for _, row in dte_mismatch.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "dte_mismatch"
            bad_rows_by_reason["dte_mismatch"].append(row_dict)

    # Near-expiry blow-ups / zero-day edge cases.
    near_expiry = df[(df["dte"] <= 1) & (df["ltp"].notna())].copy()
    near_expiry_bad = near_expiry[(near_expiry["ltp"] <= 0) | (near_expiry["ltp"] > price_ceiling)].copy()
    if not near_expiry_bad.empty:
        issues.append(f"Near-expiry unstable rows: {len(near_expiry_bad)}")
        for _, row in near_expiry_bad.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "near_expiry"
            bad_rows_by_reason["near_expiry"].append(row_dict)

    # Illiquid rows should be flagged before solver use.
    illiquid_mask = df["illiquid"].fillna(False).astype(bool)
    illiquid = df[illiquid_mask].copy()
    if not illiquid.empty:
        issues.append(f"Illiquid rows: {len(illiquid)}")
        for _, row in illiquid.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "illiquid"
            bad_rows_by_reason["illiquid"].append(row_dict)

    # Option price should not be absurdly large relative to strike.
    absurd = df[(df["ltp"].notna()) & (df["strike"].notna()) & (
        (df["ltp"] <= 0)
        | (df["ltp"] > df["strike"] * price_scale)
    )].copy()
    if not absurd.empty:
        issues.append(f"Absurd price rows: {len(absurd)}")
        for _, row in absurd.head(10).iterrows():
            row_dict = row.to_dict()
            row_dict["flagged_by"] = "absurd_price"
            bad_rows_by_reason["absurd_price"].append(row_dict)

    # Round-robin sampling across issue types: up to 2 from each, fill remaining slots.
    bad_rows_sample = []
    sample_cap = 10
    per_category_limit = 2
    
    # First pass: take up to 2 from each category.
    for reason_rows in bad_rows_by_reason.values():
        bad_rows_sample.extend(reason_rows[:per_category_limit])
        if len(bad_rows_sample) >= sample_cap:
            break
    
    # Second pass: if we have room, fill remaining slots from any category not yet exhausted.
    if len(bad_rows_sample) < sample_cap:
        for reason_rows in bad_rows_by_reason.values():
            if len(reason_rows) > per_category_limit:
                bad_rows_sample.extend(reason_rows[per_category_limit:])
                if len(bad_rows_sample) >= sample_cap:
                    break
    
    bad_rows_sample = bad_rows_sample[:sample_cap]

    ok = not issues
    return {
        "ok": ok,
        "issues": issues,
        "counts": {
            "total_rows": int(len(df)),
            "illiquid_rows": int(illiquid_mask.sum()),
            "near_expiry_rows": int(near_expiry.shape[0]),
            "bad_price_rows": int(absurd.shape[0]),
            "non_finite_rows": int(non_finite),
            "dte_mismatch_rows": int(dte_mismatch.shape[0]),
            "bad_option_type_rows": int(bad_types.shape[0]),
        },
        "bad_rows_sample": bad_rows_sample,
    }


def flag_bad_chain(
    chain_df: pd.DataFrame,
    price_ceiling: float | None = None,
    price_scale: float = 10.0,
) -> dict[str, Any]:
    """Return a structured gate result for the agent loop; bad chains are rerouted or rejected before use.
    
    Args:
        chain_df: Option chain DataFrame
        price_ceiling: Max absolute price for near-expiry rows (default 50000 for India INR scale)
        price_scale: Multiplier for max price relative to strike (default 10.0)
    """
    check = check_no_arbitrage_bounds(chain_df, price_ceiling=price_ceiling, price_scale=price_scale)
    if check["ok"]:
        return {
            "status": "pass",
            "message": "Chain passes no-arbitrage and edge-case checks.",
            "details": check,
        }
    return {
        "status": "fail",
        "message": "Chain failed sanity checks; reroute or reject for downstream analysis.",
        "details": check,
    }
