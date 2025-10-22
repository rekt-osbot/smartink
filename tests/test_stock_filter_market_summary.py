"""Tests for StockFilter market summary helpers."""

import pytest

from smartink.stock_filter import StockFilter


def _sample_market_data():
    return {
        "AAA": {"market_cap_cr": 150.0, "avg_trading_value_l": 20.0},
        "BBB": {"market_cap_cr": 90.0, "avg_trading_value_l": 5.0},
        "CCC": {"market_cap_cr": 110.0, "avg_trading_value_l": 12.0},
    }


def test_summarize_market_data_returns_expected_statistics():
    stock_filter = StockFilter(verbose=False)

    summary = stock_filter.summarize_market_data(_sample_market_data())

    assert summary["sample_size"] == 3
    assert summary["market_cap_pass_count"] == 2
    assert summary["trading_value_pass_count"] == 2
    assert summary["meets_thresholds"] == 2
    assert summary["liquidity_coverage_pct"] == pytest.approx(66.7, abs=0.1)
    assert summary["median_market_cap_cr"] == pytest.approx(110.0, rel=1e-3)
    assert summary["median_trading_value_l"] == pytest.approx(12.0, rel=1e-3)
    assert summary["data_coverage_pct"] == pytest.approx(100.0)


def test_get_last_market_summary_defaults_to_empty_dict():
    stock_filter = StockFilter(verbose=False)

    assert stock_filter.get_last_market_summary() == {}

    summary = stock_filter.summarize_market_data(_sample_market_data())
    stock_filter._last_market_summary = summary  # simulate filtering run

    assert stock_filter.get_last_market_summary() == summary
