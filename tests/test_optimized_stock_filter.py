"""Tests for the optimized stock filtering utilities."""

import sqlite3

import pandas as pd

from smartink.database_manager import DatabaseManager
from smartink.optimized_stock_filter import OptimizedStockFilter, PostFetchFilter


def test_get_series_filtered_stocks_excludes_series(tmp_path):
    db_path = tmp_path / "tradable_stocks.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE tradable_stocks (
            symbol TEXT PRIMARY KEY,
            series TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO tradable_stocks (symbol, series) VALUES (?, ?)",
        [
            ("AAA", "EQ"),
            ("BBB", "BE"),
            ("CCC", "EQ"),
            ("DDD", "BZ"),
        ],
    )
    conn.commit()
    conn.close()

    opt_filter = OptimizedStockFilter(verbose=False)
    opt_filter.db_manager = DatabaseManager(db_file=str(db_path), verbose=False)

    filtered = opt_filter.get_series_filtered_stocks(excluded_series=["BE", "BZ"])
    assert filtered == ["AAA", "CCC"]


def test_post_fetch_filter_removes_low_volume_stocks():
    post_filter = PostFetchFilter(min_daily_value_l=10.0)

    high_volume = pd.DataFrame(
        {
            "Close": [100.0, 102.0, 101.5],
            "Volume": [120_000, 125_000, 118_000],
        }
    )
    low_volume = pd.DataFrame(
        {
            "Close": [25.0, 24.5, 24.8],
            "Volume": [2_000, 1_800, 1_900],
        }
    )

    filtered = post_filter.filter_by_volume({"HIGH": high_volume, "LOW": low_volume})

    assert list(filtered.keys()) == ["HIGH"]
    assert filtered["HIGH"].equals(high_volume)
