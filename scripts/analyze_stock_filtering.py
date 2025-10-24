#!/usr/bin/env python3
"""Analyze current stock filtering inefficiencies and potential optimizations."""

import sqlite3
from typing import Tuple

import pandas as pd


def analyze_stock_categories() -> Tuple[int, int, int]:
    """Analyze stock distribution by categories."""
    conn = sqlite3.connect("tradable_stocks.db")

    query = "SELECT series, COUNT(*) FROM tradable_stocks GROUP BY series ORDER BY COUNT(*) DESC"
    df_series = pd.read_sql_query(query, conn)

    print("Stock distribution by series:")
    print(df_series.to_string(index=False))

    total_stocks = df_series["COUNT(*)"].sum()
    be_bz_stocks = df_series[df_series["series"].isin(["BE", "BZ"])]["COUNT(*)"].sum()
    eq_stocks = df_series[df_series["series"] == "EQ"]["COUNT(*)"].sum()

    print("\nSummary:")
    print(f"Total stocks: {total_stocks}")
    print(f"EQ stocks: {eq_stocks}")
    print(f"BE + BZ stocks: {be_bz_stocks}")
    print(f"Potential reduction: {be_bz_stocks} stocks ({be_bz_stocks/total_stocks*100:.1f}%)")

    print("\nSample BE stocks:")
    be_stocks = pd.read_sql_query(
        "SELECT symbol, name_of_company FROM tradable_stocks WHERE series = 'BE' LIMIT 10", conn
    )
    print(be_stocks.to_string(index=False))

    print("\nSample BZ stocks:")
    bz_stocks = pd.read_sql_query(
        "SELECT symbol, name_of_company FROM tradable_stocks WHERE series = 'BZ' LIMIT 10", conn
    )
    print(bz_stocks.to_string(index=False))

    conn.close()
    return total_stocks, eq_stocks, be_bz_stocks


def check_current_processing() -> None:
    """Check how current system processes stocks."""
    print("\n" + "=" * 60)
    print("CURRENT PROCESSING ANALYSIS")
    print("=" * 60)

    try:
        from smartink.stock_data_fetcher import StockDataFetcher

        fetcher = StockDataFetcher()

        all_stocks = fetcher.get_stocks_from_database(use_popular_only=False)
        popular_stocks = fetcher.get_stocks_from_database(use_popular_only=True)

        print(f"Current fetcher gets {len(all_stocks)} stocks from database")
        print(f"Popular stocks filter reduces to {len(popular_stocks)} stocks")

        conn = sqlite3.connect("tradable_stocks.db")
        cursor = conn.cursor()

        if all_stocks:
            placeholders = ",".join(["?" for _ in all_stocks])
            query = f"SELECT series, COUNT(*) FROM tradable_stocks WHERE symbol IN ({placeholders}) GROUP BY series"
            cursor.execute(query, all_stocks)
            fetched_series = cursor.fetchall()

            print("\nSeries distribution in fetched stocks:")
            for series, count in fetched_series:
                print(f"  {series}: {count} stocks")

        conn.close()

    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"Error analyzing current processing: {exc}")


if __name__ == "__main__":
    print("STOCK FILTERING ANALYSIS")
    print("=" * 60)

    total, eq, be_bz = analyze_stock_categories()

    check_current_processing()

    print("\n" + "=" * 60)
    print("OPTIMIZATION OPPORTUNITIES")
    print("=" * 60)
    print(f"1. Filter out BE/BZ categories: Save {be_bz} API calls ({be_bz/total*100:.1f}%)")
    print(f"2. Add market cap filtering: Further reduce low-value stocks")
    print(f"3. Add trading volume filtering: Focus on liquid stocks only")
    print(f"4. Estimated processing time reduction: {be_bz/total*100:.1f}% - {(be_bz/total*100)*1.5:.1f}%")
