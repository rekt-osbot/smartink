"""Tests for lightweight count helpers in StockDataManager."""

import pandas as pd

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
            {"symbol": "AAA", "date": "2024-01-01", "sma_20": 97.0},
            {"symbol": "AAA", "date": "2024-01-02", "sma_20": 100.0},
            {"symbol": "BBB", "date": "2024-01-01", "sma_20": 205.0},
            {"symbol": "BBB", "date": "2024-01-02", "sma_20": 206.0},
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
