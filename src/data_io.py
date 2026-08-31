"""Load option-chain files and generate a runnable sample chain if none exists."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.calc.iv import bs_price

REQUIRED_COLUMNS = ["timestamp", "expiry", "strike", "option_type", "ltp", "illiquid"]
DEFAULT_CSV_PATH = Path("OPTIONS_DATA/nifty_options.csv")


def generate_sample_chain() -> pd.DataFrame:
    """Build a small internally consistent Nifty-style chain for local demos."""
    timestamps = pd.to_datetime(
        [
            "2026-08-28 10:30:00",
            "2026-08-28 11:30:00",
            "2026-08-28 13:15:00",
            "2026-08-28 15:20:00",
        ]
    )
    # ~27 DTE so 25-delta strikes sit well inside the chain, not jammed at ATM.
    expiry = pd.Timestamp("2026-09-24")
    spot = 22000.0
    rate = 0.065
    strikes = list(range(20800, 23300, 100))
    rows: list[dict] = []

    for ts in timestamps:
        dte = int((expiry.normalize() - ts.normalize()).days)
        time_to_expiry = max(dte, 1) / 365.0
        forward = spot + (ts.hour - 10) * 12.0
        for strike in strikes:
            moneyness = (strike - forward) / forward
            call_vol = 0.12 + abs(min(moneyness, 0.0)) * 0.18
            put_vol = 0.17 + abs(max(moneyness, 0.0)) * 0.22
            call_price = float(bs_price(forward, strike, time_to_expiry, rate, call_vol, "c"))
            put_price = float(bs_price(forward, strike, time_to_expiry, rate, put_vol, "p"))
            if call_price != call_price or put_price != put_price:
                continue
            common = {
                "timestamp": ts,
                "expiry": expiry,
                "strike": float(strike),
                "illiquid": False,
                "dte": dte,
                "underlying": "NIFTY",
            }
            rows.append({**common, "option_type": "CE", "ltp": round(max(call_price, 0.05), 2)})
            rows.append({**common, "option_type": "PE", "ltp": round(max(put_price, 0.05), 2)})

    return pd.DataFrame(rows)


def ensure_sample_csv(csv_path: str | Path = DEFAULT_CSV_PATH) -> Path:
    """Create OPTIONS_DATA/nifty_options.csv when the file is missing."""
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return path
    generate_sample_chain().to_csv(path, index=False)
    return path


def load_chain(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Load a CSV/parquet chain, or generate the bundled sample file."""
    path = ensure_sample_csv(csv_path or DEFAULT_CSV_PATH)
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Option chain is missing required columns: {missing}")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["expiry"] = pd.to_datetime(df["expiry"])
    df["option_type"] = df["option_type"].astype(str).str.upper()
    df["illiquid"] = df["illiquid"].fillna(False).astype(bool)
    if "dte" not in df.columns:
        df["dte"] = (df["expiry"].dt.normalize() - df["timestamp"].dt.normalize()).dt.days
    return df
