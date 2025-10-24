"""Tests for the database manager helpers."""

import pandas as pd

from smartink.database_manager import DatabaseManager


def test_create_and_populate_table_replaces_content(tmp_path):
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_file=str(db_path), verbose=False)
    manager.table_name = "temp_table"

    df = pd.DataFrame(
        {
            "symbol": ["ABC", "XYZ"],
            "listing_date": pd.to_datetime(["2024-01-15", "2024-01-16"]),
            "market_cap": [123.45, 456.78],
            "is_active": [True, False],
        }
    )

    assert manager.create_and_populate_table(df) is True

    with manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(temp_table)")
        schema = {row[1]: row[2] for row in cursor.fetchall()}

        assert schema["symbol"] == "TEXT"
        assert schema["listing_date"] in {"DATE", "TEXT"}
        assert schema["market_cap"] == "REAL"
        assert schema["is_active"] == "INTEGER"

        cursor.execute("SELECT COUNT(*) FROM temp_table")
        row_count = cursor.fetchone()[0]

    assert row_count == len(df)
