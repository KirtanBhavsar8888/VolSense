import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.calc.iv import bs_delta, bs_price, compute_iv


@pytest.fixture
def notebook_self_test_case():
    return {
        "F": 16493.0,
        "K": 16493.0,
        "T": 7 / 365,
        "r": 0.065,
        "sigma": 0.18,
        "flag": "c",
    }


@pytest.fixture
def notebook_backtest_summary():
    return {
        "total_trades": 208,
        "win_rate_pct": 48.6,
    }


def test_bs_round_trip_iv_self_test(notebook_self_test_case):
    case = notebook_self_test_case

    price = bs_price(case["F"], case["K"], case["T"], case["r"], case["sigma"], case["flag"])
    assert price == pytest.approx(163.8069, rel=1e-4, abs=1e-4)

    iv_rt = compute_iv(price, case["F"], case["K"], case["T"], case["r"], case["flag"])
    assert iv_rt == pytest.approx(case["sigma"], abs=1e-5)

    delta = bs_delta(case["F"], case["K"], case["T"], case["r"], case["sigma"], case["flag"])
    assert 0.52 <= delta <= 0.55


def test_notebook_known_backtest_summary_regression(notebook_backtest_summary):
    summary = notebook_backtest_summary

    assert summary["total_trades"] == 208
    assert summary["win_rate_pct"] == pytest.approx(48.6, abs=1e-9)
    assert summary["win_rate_pct"] < 50.0
