"""Tests for the database manager helpers."""

import pandas as pd

from smartink.database_manager import DatabaseManager


def test_generate_create_table_sql_uses_type_mapping():
    manager = DatabaseManager(verbose=False)
    df = pd.DataFrame(
        {
            "symbol": ["ABC"],
            "listing_date": pd.to_datetime(["2024-01-15"]),
            "market_cap": [123.45],
            "is_active": [True],
        }
    )

    sql = manager.generate_create_table_sql(df)

    # The CREATE TABLE statement should include our mapped column types
    assert "symbol TEXT" in sql
    assert "listing_date DATE" in sql
    assert "market_cap REAL" in sql
    # Booleans are stored as INTEGER in SQLite in our mapping
    assert "is_active INTEGER" in sql
