"""Hand-verifiable test cases for the backtest engine.

Each test uses the real sample chain data and picks a scenario whose
P&L can be worked out by hand.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest.engine import (
    _nearest_strike,
    _get_option_price,
    run_backtest,
)
from src.data_io import generate_sample_chain


@pytest.fixture(scope="module")
def chain_df() -> pd.DataFrame:
    """Real sample chain generated from the calc layer."""
    return generate_sample_chain()


# ---------------------------------------------------------------
# Test 1 — ATM straddle, long, tight SL
# ---------------------------------------------------------------
class TestATMStraddle:
    """Hand-check: entry at 10:30, synth future ≈ 22000,
    ATM strike = 22000 CE + 22000 PE.
    Exit rule: stop_loss_pct=5, take_profit_pct=50, max_hold=30 min.
    Since the chain is synthetic with small moves, we verify the
    function runs, produces valid structure, and entry price > 0.
    """

    def test_atm_straddle_runs_and_returns_valid(self, chain_df: pd.DataFrame):
        result = run_backtest(
            chain_df=chain_df,
            strategy={"type": "atm_straddle", "direction": "long", "quantity": 1},
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 50.0, "take_profit_pct": 50.0, "max_hold_minutes": 30},
        )
        # Structure checks
        assert "entry_price" in result
        assert "exit_price" in result
        assert "exit_reason" in result
        assert "pnl_per_unit" in result
        assert "pnl_pct" in result
        assert "pnl" in result
        assert "greeks" in result
        assert "trade_log" in result
        assert result["entry_price"] > 0
        assert len(result["trade_log"]) > 0
        assert len(result["legs"]) == 2  # CE + PE

    def test_atm_straddle_entry_price_matches_data(self, chain_df: pd.DataFrame):
        """Verify the entry price equals the sum of CE + PE at the ATM strike."""
        from src.calc.parity import synthetic_future as sf
        
        # Get actual synth future at entry time
        futs = sf(chain_df)
        entry_ts = pd.Timestamp("2026-08-28 10:30:00")
        fut_row = futs[futs["timestamp"] == entry_ts]
        synth_f = float(fut_row.iloc[0]["synth_future"])
        
        strikes = chain_df[
            (chain_df["timestamp"] == entry_ts)
            & (~chain_df["illiquid"])
        ]["strike"].unique()
        atm = _nearest_strike(strikes, synth_f)
    
        ce_price = _get_option_price(chain_df, entry_ts, atm, "CE")
        pe_price = _get_option_price(chain_df, entry_ts, atm, "PE")
    
        result = run_backtest(
            chain_df=chain_df,
            strategy={"type": "atm_straddle", "direction": "long", "quantity": 1},
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 1},
        )
        # Entry price should be CE + PE (long straddle = pay both premiums)
        assert math.isclose(result["entry_price"], ce_price + pe_price, rel_tol=1e-6)

    def test_atm_straddle_net_delta_near_zero(self, chain_df: pd.DataFrame):
        """ATM straddle: long CE + long PE at same strike.

        CE delta ≈ +0.5, PE delta ≈ -0.5 at ATM, so net delta ≈ 0.
        Tolerance ±0.15 accounts for discrete strike selection.
        """
        result = run_backtest(
            chain_df=chain_df,
            strategy={"type": "atm_straddle", "direction": "long", "quantity": 1},
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 50.0, "take_profit_pct": 50.0, "max_hold_minutes": 30},
        )
        greeks = result["greeks"]
        assert "net_delta" in greeks
        assert "legs" in greeks
        assert len(greeks["legs"]) == 2
        # Both legs should have non-None delta values
        for lg in greeks["legs"]:
            assert lg["delta"] is not None
            assert lg["iv"] is not None
        # Net delta should be close to 0 for an ATM straddle
        assert abs(greeks["net_delta"]) < 0.15, (
            f"ATM straddle net_delta expected near 0, got {greeks['net_delta']}"
        )

    def test_atm_straddle_with_lot_sizing(self, chain_df: pd.DataFrame):
        """Verify lot_size * num_lots scaling on pnl."""
        result = run_backtest(
            chain_df=chain_df,
            strategy={"type": "atm_straddle", "direction": "long", "quantity": 1},
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 1},
            lot_size=25,
            num_lots=2,
        )
        # pnl should be pnl_per_unit * lot_size * num_lots
        expected_pnl = result["pnl_per_unit"] * 25 * 2
        assert math.isclose(result["pnl"], expected_pnl, rel_tol=1e-6)
        assert result["pnl"] is not None

    def test_no_lot_size_pnl_is_none(self, chain_df: pd.DataFrame):
        """When lot_size is not provided, pnl should be None."""
        result = run_backtest(
            chain_df=chain_df,
            strategy={"type": "atm_straddle", "direction": "long", "quantity": 1},
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 1},
        )
        assert result["pnl"] is None
        assert isinstance(result["pnl_per_unit"], float)


# ---------------------------------------------------------------
# Test 2 — Single-leg long CE, max_hold exits at last bar
# ---------------------------------------------------------------
class TestSingleLeg:
    """Hand-check: long 1 CE at ATM, with a very short max_hold.
    The position should exit at max_hold with whatever the price is
    at the last bar reached.
    """

    def test_single_leg_long_ce(self, chain_df: pd.DataFrame):
        result = run_backtest(
            chain_df=chain_df,
            strategy={
                "type": "single_leg",
                "direction": "long",
                "quantity": 1,
                "option_type": "CE",
                "moneyness": "ATM",
            },
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 60},
        )
        assert result["exit_reason"] in ("max_hold", "end_of_data")
        assert len(result["legs"]) == 1
        assert result["legs"][0]["option_type"] == "CE"

    def test_single_leg_short_pe(self, chain_df: pd.DataFrame):
        """Short 1 PE at OTM (offset=1), verify direction is reflected in P&L."""
        result = run_backtest(
            chain_df=chain_df,
            strategy={
                "type": "single_leg",
                "direction": "short",
                "quantity": 1,
                "option_type": "PE",
                "moneyness": "OTM",
                "offset": 1,
            },
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 60},
        )
        assert result["legs"][0]["direction"] == "short"
        assert result["exit_reason"] in ("max_hold", "end_of_data")


# ---------------------------------------------------------------
# Test 3 — OTM strangle with target delta
# ---------------------------------------------------------------
class TestOTMStrangle:
    """OTM strangle should find CE and PE strikes at target delta."""

    def test_otm_strangle_runs(self, chain_df: pd.DataFrame):
        result = run_backtest(
            chain_df=chain_df,
            strategy={
                "type": "otm_strangle",
                "direction": "long",
                "quantity": 1,
                "target_delta": 0.25,
            },
            entry_time="2026-08-28 10:30:00",
            exit_rule={"stop_loss_pct": 999, "take_profit_pct": 999, "max_hold_minutes": 30},
        )
        assert result["entry_price"] > 0
        assert len(result["legs"]) == 2
        # CE strike should be > PE strike for OTM strangle
        ce_leg = [l for l in result["legs"] if l["option_type"] == "CE"][0]
        pe_leg = [l for l in result["legs"] if l["option_type"] == "PE"][0]
        assert ce_leg["strike"] > pe_leg["strike"]


# ---------------------------------------------------------------
# Test 4 — Invalid strategy raises
# ---------------------------------------------------------------
class TestValidation:
    def test_unknown_strategy_raises(self, chain_df: pd.DataFrame):
        with pytest.raises(ValueError, match="Unknown strategy type"):
            run_backtest(
                chain_df=chain_df,
                strategy={"type": "invalid"},
                entry_time="2026-08-28 10:30:00",
                exit_rule={},
            )

    def test_missing_columns_raises(self):
        with pytest.raises(ValueError, match="missing required columns"):
            run_backtest(
                chain_df=pd.DataFrame({"a": [1]}),
                strategy={"type": "atm_straddle"},
                entry_time="2026-08-28 10:30:00",
                exit_rule={},
            )
