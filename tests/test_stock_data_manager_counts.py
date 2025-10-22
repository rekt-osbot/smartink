"""Tests for lightweight count helpers in StockDataManager."""

import pandas as pd
import pytest

from smartink.stock_data_manager import StockDataManager


def _create_manager_with_sample_data(tmp_path):
    manager = StockDataManager(verbose=False)
    manager.db_file = str(tmp_path / "test_counts.db")
    assert manager.setup_extended_schema()

    price_data = pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "date": "2024-01-01",
                "open": 100.0,
                "high": 100.0,
                "low": 95.0,
                "close": 98.0,
                "volume": 1000,
            },
            {
                "symbol": "AAA",
                "date": "2024-01-02",
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 104.0,
                "volume": 1100,
            },
            {
                "symbol": "BBB",
                "date": "2024-01-01",
                "open": 200.0,
                "high": 210.0,
                "low": 198.0,
                "close": 205.0,
                "volume": 2000,
            },
            {
                "symbol": "BBB",
                "date": "2024-01-02",
                "open": 210.0,
                "high": 212.0,
                "low": 205.0,
                "close": 204.0,
                "volume": 2100,
            },
        ]
    )
    indicator_data = pd.DataFrame(
        [
            {"symbol": "AAA", "date": "2024-01-01", "sma_20": 97.0, "sma_50": 96.0, "rsi_14": 55.0},
            {"symbol": "AAA", "date": "2024-01-02", "sma_20": 100.0, "sma_50": 99.0, "rsi_14": 65.0},
            {"symbol": "BBB", "date": "2024-01-01", "sma_20": 205.0, "sma_50": 208.0, "rsi_14": 48.0},
            {"symbol": "BBB", "date": "2024-01-02", "sma_20": 206.0, "sma_50": 210.0, "rsi_14": 35.0},
        ]
    )

    assert manager.insert_price_data(price_data)
    assert manager.insert_indicators_data(indicator_data)

    return manager


def test_count_total_stocks_with_data_uses_distinct_symbols(tmp_path):
    manager = _create_manager_with_sample_data(tmp_path)

    assert manager.count_total_stocks_with_data() == 2


def test_count_stocks_above_sma_respects_latest_data(tmp_path):
    manager = _create_manager_with_sample_data(tmp_path)

    assert manager.count_stocks_above_sma(20) == 1
    assert manager.count_stocks_above_sma(20, max_distance=3.0) == 0


def test_count_open_high_patterns_detects_breakouts(tmp_path):
    manager = _create_manager_with_sample_data(tmp_path)

    assert manager.count_open_high_patterns() == 1


def test_market_health_snapshot_includes_trend_and_rsi_counts(tmp_path):
    manager = _create_manager_with_sample_data(tmp_path)

    snapshot = manager.get_market_health_snapshot()

    assert snapshot['total_stocks'] == 2
    assert snapshot['above_sma_20'] == 1
    assert snapshot['above_sma_50'] == 1
    assert snapshot['bullish_trend'] == 1
    assert snapshot['bearish_trend'] == 1
    assert snapshot['neutral_trend'] == 0
    assert snapshot['rsi_overbought'] == 1
    assert snapshot['rsi_oversold'] == 1
    assert snapshot['avg_rsi'] == pytest.approx(50.0, rel=1e-5)
    assert snapshot['avg_trend_strength'] == pytest.approx(-0.45, abs=0.02)
