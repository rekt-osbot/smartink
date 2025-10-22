"""
Stock data manager for handling OHLCV data storage and retrieval.
This module extends the database schema to include price and volume data.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from smartink.database_manager import DatabaseManager
from smartink.utils import print_step
from smartink.config import DB_FILE, DATE_FORMAT


class StockDataManager(DatabaseManager):
    """Extended database manager for stock OHLCV data."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the stock data manager."""
        super().__init__(verbose=verbose)
        self.price_table = "stock_prices"
        self.indicators_table = "stock_indicators"
    
    def create_price_table(self) -> bool:
        """
        Create table for storing OHLCV data.
        
        Returns:
            bool: True if successful
        """
        try:
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.price_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            );
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_sql)
                
                # Create indexes for better performance
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.price_table}_symbol ON {self.price_table}(symbol);")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.price_table}_date ON {self.price_table}(date);")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.price_table}_symbol_date ON {self.price_table}(symbol, date);")
                
                conn.commit()
                self._log(f"Created table: {self.price_table}")
                return True
                
        except Exception as e:
            self._log(f"Error creating price table: {e}")
            return False
    
    def create_indicators_table(self) -> bool:
        """
        Create table for storing technical indicators.
        
        Returns:
            bool: True if successful
        """
        try:
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.indicators_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                sma_20 REAL,
                sma_50 REAL,
                rsi_14 REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            );
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_sql)
                
                # Create indexes
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.indicators_table}_symbol ON {self.indicators_table}(symbol);")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.indicators_table}_date ON {self.indicators_table}(date);")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.indicators_table}_symbol_date ON {self.indicators_table}(symbol, date);")
                
                conn.commit()
                self._log(f"Created table: {self.indicators_table}")
                return True
                
        except Exception as e:
            self._log(f"Error creating indicators table: {e}")
            return False
    
    def setup_extended_schema(self) -> bool:
        """
        Set up the extended database schema for stock data.
        
        Returns:
            bool: True if successful
        """
        self._log("Setting up extended database schema...")
        
        success = True
        success &= self.create_price_table()
        success &= self.create_indicators_table()
        
        if success:
            self._log("✓ Extended database schema created successfully")
        else:
            self._log("✗ Failed to create extended database schema")
        
        return success
    
    def insert_price_data(self, data: pd.DataFrame) -> bool:
        """
        Insert or update OHLCV data into the price table using proper upsert logic.

        Args:
            data (pd.DataFrame): DataFrame with OHLCV data

        Returns:
            bool: True if successful
        """
        try:
            # Prepare data for insertion
            df_to_insert = data.copy()

            # Ensure date is in string format
            if 'date' in df_to_insert.columns:
                df_to_insert['date'] = pd.to_datetime(df_to_insert['date']).dt.strftime(DATE_FORMAT)

            # Select only the columns we need
            required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            df_to_insert = df_to_insert[required_columns]

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create temporary table for bulk upsert
                temp_table = f"{self.price_table}_temp"
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")

                # Create temporary table with same structure
                cursor.execute(f"""
                CREATE TEMPORARY TABLE {temp_table} (
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    PRIMARY KEY (symbol, date)
                )
                """)

                # Insert data into temporary table
                df_to_insert.to_sql(temp_table, conn, if_exists='append', index=False)

                # Perform upsert using INSERT OR REPLACE
                cursor.execute(f"""
                INSERT OR REPLACE INTO {self.price_table}
                (symbol, date, open, high, low, close, volume, created_at)
                SELECT
                    symbol, date, open, high, low, close, volume,
                    COALESCE(
                        (SELECT created_at FROM {self.price_table} p
                         WHERE p.symbol = {temp_table}.symbol AND p.date = {temp_table}.date),
                        CURRENT_TIMESTAMP
                    ) as created_at
                FROM {temp_table}
                """)

                rows_affected = cursor.rowcount

                # Clean up temporary table
                cursor.execute(f"DROP TABLE {temp_table}")

                conn.commit()
                self._log(f"Upserted {rows_affected} price records")
                return True

        except Exception as e:
            self._log(f"Error upserting price data: {e}")
            return False
    
    def insert_indicators_data(self, data: pd.DataFrame) -> bool:
        """
        Insert or update technical indicators data using proper upsert logic.

        Args:
            data (pd.DataFrame): DataFrame with indicators data

        Returns:
            bool: True if successful
        """
        try:
            df_to_insert = data.copy()

            # Ensure date is in string format
            if 'date' in df_to_insert.columns:
                df_to_insert['date'] = pd.to_datetime(df_to_insert['date']).dt.strftime(DATE_FORMAT)

            # Select only the columns we need
            available_columns = ['symbol', 'date']
            indicator_columns = ['sma_20', 'sma_50', 'rsi_14']

            for col in indicator_columns:
                if col in df_to_insert.columns:
                    available_columns.append(col)

            df_to_insert = df_to_insert[available_columns]

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create temporary table for bulk upsert
                temp_table = f"{self.indicators_table}_temp"
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")

                # Create temporary table with same structure
                cursor.execute(f"""
                CREATE TEMPORARY TABLE {temp_table} (
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    sma_20 REAL,
                    sma_50 REAL,
                    rsi_14 REAL,
                    PRIMARY KEY (symbol, date)
                )
                """)

                # Insert data into temporary table
                df_to_insert.to_sql(temp_table, conn, if_exists='append', index=False)

                # Perform upsert using INSERT OR REPLACE
                cursor.execute(f"""
                INSERT OR REPLACE INTO {self.indicators_table}
                (symbol, date, sma_20, sma_50, rsi_14, created_at)
                SELECT
                    symbol, date, sma_20, sma_50, rsi_14,
                    COALESCE(
                        (SELECT created_at FROM {self.indicators_table} i
                         WHERE i.symbol = {temp_table}.symbol AND i.date = {temp_table}.date),
                        CURRENT_TIMESTAMP
                    ) as created_at
                FROM {temp_table}
                """)

                rows_affected = cursor.rowcount

                # Clean up temporary table
                cursor.execute(f"DROP TABLE {temp_table}")

                conn.commit()
                self._log(f"Upserted {rows_affected} indicator records")
                return True

        except Exception as e:
            self._log(f"Error upserting indicators data: {e}")
            return False
    
    def get_latest_prices(self, symbol: str = None, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Get latest price data for stocks.
        
        Args:
            symbol (str, optional): Specific symbol to get data for
            limit (int): Maximum number of records to return
            
        Returns:
            Optional[pd.DataFrame]: Price data or None
        """
        try:
            if symbol:
                query = f"""
                SELECT * FROM {self.price_table} 
                WHERE symbol = ? 
                ORDER BY date DESC 
                LIMIT ?
                """
                params = (symbol, limit)
            else:
                query = f"""
                SELECT * FROM {self.price_table} 
                ORDER BY date DESC, symbol 
                LIMIT ?
                """
                params = (limit,)
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df if not df.empty else None
                
        except Exception as e:
            self._log(f"Error getting latest prices: {e}")
            return None
    
    def get_stocks_near_sma_breakout(self, sma_period: int = 20, max_distance: float = 5.0) -> Optional[pd.DataFrame]:
        """Return enhanced breakout intelligence for stocks near a simple moving average."""

        try:
            sma_column = f"sma_{sma_period}"

            query = f"""
            WITH enriched AS (
                SELECT
                    p.symbol,
                    p.date,
                    p.open,
                    p.high,
                    p.low,
                    p.close,
                    p.volume,
                    i.{sma_column} AS target_sma,
                    i.sma_20,
                    i.sma_50,
                    i.rsi_14,
                    LAG(p.open) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_open,
                    LAG(p.high) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_high,
                    LAG(p.low) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_low,
                    LAG(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_close,
                    LAG(p.volume) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_volume,
                    LAG(i.{sma_column}) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_target_sma,
                    LAG(i.sma_20) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_sma_20,
                    LAG(i.sma_50) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_sma_50,
                    LAG(i.rsi_14) OVER (PARTITION BY p.symbol ORDER BY p.date) AS prev_rsi_14,
                    AVG(p.volume) OVER (
                        PARTITION BY p.symbol
                        ORDER BY p.date
                        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                    ) AS avg_volume_5,
                    AVG(p.close) OVER (
                        PARTITION BY p.symbol
                        ORDER BY p.date
                        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                    ) AS avg_close_5,
                    MAX(p.high) OVER (
                        PARTITION BY p.symbol
                        ORDER BY p.date
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) AS rolling_high_20,
                    MIN(p.low) OVER (
                        PARTITION BY p.symbol
                        ORDER BY p.date
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) AS rolling_low_20,
                    ROW_NUMBER() OVER (PARTITION BY p.symbol ORDER BY p.date DESC) AS rn
                FROM {self.price_table} p
                JOIN {self.indicators_table} i ON p.symbol = i.symbol AND p.date = i.date
                WHERE i.{sma_column} IS NOT NULL
                    AND i.{sma_column} != 0
            )
            SELECT *
            FROM enriched
            WHERE rn = 1
            """

            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)

            if df.empty:
                return None

            df = df.drop(columns=["rn"])

            sma_label = f"sma_{sma_period}"
            prev_sma_label = f"prev_sma_{sma_period}"
            df = df.rename(columns={
                "target_sma": sma_label,
                "prev_target_sma": prev_sma_label
            })

            def safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
                denominator_safe = denominator.replace({0: np.nan})
                return (numerator / denominator_safe) * 100

            df["trend_strength"] = safe_pct(df["sma_20"] - df["sma_50"], df["sma_50"])
            df["trend_bias"] = np.select(
                [
                    (df["sma_20"].notna()) & (df["sma_50"].notna()) & (df["sma_20"] > df["sma_50"]),
                    (df["sma_20"].notna()) & (df["sma_50"].notna()) & (df["sma_20"] < df["sma_50"])
                ],
                ["Bullish Bias", "Bearish Bias"],
                default="Neutral Bias"
            )
            df["rsi_signal"] = np.select(
                [
                    df["rsi_14"].ge(60),
                    df["rsi_14"].le(40),
                    df["rsi_14"].isna()
                ],
                ["Overbought", "Oversold", "No Signal"],
                default="Neutral"
            )

            df["percentage_from_sma"] = safe_pct(df["close"] - df[sma_label], df[sma_label])
            df["prev_percentage_from_sma"] = safe_pct(
                df["prev_close"] - df[prev_sma_label], df[prev_sma_label]
            )
            df["distance_change_pct"] = df["percentage_from_sma"] - df["prev_percentage_from_sma"]
            df["high_break_pct"] = safe_pct(df["high"] - df[sma_label], df[sma_label])
            df["low_break_pct"] = safe_pct(df["low"] - df[sma_label], df[sma_label])
            df["close_vs_prev_close_pct"] = safe_pct(df["close"] - df["prev_close"], df["prev_close"])
            df["volume_surge_ratio"] = np.where(
                (df["avg_volume_5"].notna()) & (df["avg_volume_5"] > 0),
                df["volume"] / df["avg_volume_5"],
                np.nan
            )
            df["momentum_5"] = safe_pct(df["close"] - df["avg_close_5"], df["avg_close_5"])
            df["twenty_day_breakout_pct"] = safe_pct(df["close"] - df["rolling_high_20"], df["rolling_high_20"])

            small_tolerance = 0.1
            df["position_vs_sma"] = np.select(
                [
                    df["percentage_from_sma"] > small_tolerance,
                    df["percentage_from_sma"] < -small_tolerance
                ],
                ["Above", "Below"],
                default="At"
            )

            breakout_confirm_pct = 0.35
            retest_buffer_pct = 0.6
            trigger_buffer_pct = 0.8

            pct = df["percentage_from_sma"]
            prev_pct = df["prev_percentage_from_sma"]
            high_break = df["high_break_pct"]
            low_break = df["low_break_pct"]
            distance_change = df["distance_change_pct"].fillna(0)
            momentum = df["momentum_5"].fillna(0)

            fresh_breakout = (
                (pct >= breakout_confirm_pct) &
                (
                    prev_pct.isna() |
                    (prev_pct <= breakout_confirm_pct / 2) |
                    (distance_change >= breakout_confirm_pct)
                )
            )

            fresh_breakdown = (
                (pct <= -breakout_confirm_pct) &
                (
                    prev_pct.isna() |
                    (prev_pct >= -breakout_confirm_pct / 2) |
                    (distance_change <= -breakout_confirm_pct)
                )
            )

            retest_hold = (
                (pct > breakout_confirm_pct / 2) &
                (low_break >= -retest_buffer_pct) &
                (low_break <= breakout_confirm_pct) &
                (~fresh_breakout)
            )

            momentum_continuation = (
                (pct > breakout_confirm_pct / 2) &
                (prev_pct > breakout_confirm_pct / 2) &
                (distance_change > 0) &
                (momentum > 0) &
                (~fresh_breakout) &
                (~retest_hold)
            )

            failed_breakout = (
                (pct < -small_tolerance) &
                (high_break >= breakout_confirm_pct) &
                (distance_change < 0)
            )

            trigger_watch = (
                (pct >= -trigger_buffer_pct) &
                (pct <= breakout_confirm_pct) &
                (high_break >= -small_tolerance) &
                (~fresh_breakout) &
                (~retest_hold) &
                (~momentum_continuation)
            )

            bearish_drift = (
                (pct < -small_tolerance) &
                (~fresh_breakdown) &
                (~failed_breakout)
            )

            df["breakout_status"] = "At SMA"
            df.loc[df["position_vs_sma"] == "Above", "breakout_status"] = "Holding Above"
            df.loc[df["position_vs_sma"] == "Below", "breakout_status"] = "Holding Below"
            df.loc[fresh_breakout, "breakout_status"] = "Fresh Breakout Above"
            df.loc[fresh_breakdown, "breakout_status"] = "Fresh Breakdown Below"

            default_signal = "Range-Bound / No Signal"
            signal = np.array([default_signal] * len(df))
            signal[fresh_breakout] = "Fresh Breakout (Confirmed)"
            signal[fresh_breakdown] = "Fresh Breakdown (Confirmed)"
            signal[retest_hold] = "Retest & Hold Above"
            signal[momentum_continuation] = "Momentum Continuation"
            signal[trigger_watch & (pct >= 0)] = "Breakout Watch (Compression)"
            signal[trigger_watch & (pct < 0)] = "Breakout Watch (Slightly Below)"
            signal[failed_breakout] = "Failed Breakout - Caution"
            signal[bearish_drift & (~fresh_breakdown)] = "Bearish Drift / Breakdown Risk"
            df["breakout_signal"] = signal

            base_confidence = np.full(len(df), 40.0)
            base_confidence[fresh_breakout] = 70.0
            base_confidence[retest_hold] = 60.0
            base_confidence[momentum_continuation] = 55.0
            base_confidence[trigger_watch & (pct >= 0)] = 50.0
            base_confidence[trigger_watch & (pct < 0)] = 45.0
            base_confidence[failed_breakout] = 25.0
            base_confidence[fresh_breakdown] = 65.0
            base_confidence[bearish_drift & (~fresh_breakdown)] = 45.0

            confidence = base_confidence
            confidence += np.clip(pct, -3, 3)

            vol_adj = np.clip(np.nan_to_num(df["volume_surge_ratio"], nan=1.0) - 1, -1, 3)
            confidence += vol_adj * 5

            confidence += np.clip(momentum / 2, -5, 5)

            if "trend_bias" in df.columns:
                confidence += np.where(
                    df["trend_bias"] == "Bullish Bias",
                    np.where(pct >= 0, 5, -5),
                    0
                )
                confidence += np.where(
                    df["trend_bias"] == "Bearish Bias",
                    np.where(pct < 0, 5, -5),
                    0
                )

            if "rsi_signal" in df.columns:
                confidence += np.where(
                    df["rsi_signal"] == "Overbought",
                    np.where(pct >= 0, -5, 5),
                    0
                )
                confidence += np.where(
                    df["rsi_signal"] == "Oversold",
                    np.where(pct < 0, -5, 5),
                    0
                )

            df["breakout_confidence"] = np.clip(confidence, 0, 100)

            signal_priority = np.full(len(df), 6.0)
            signal_priority[fresh_breakout] = 1.0
            signal_priority[retest_hold] = 2.0
            signal_priority[momentum_continuation] = 3.0
            signal_priority[trigger_watch & (pct >= 0)] = 3.5
            signal_priority[trigger_watch & (pct < 0)] = 4.0
            signal_priority[failed_breakout] = 4.5
            signal_priority[fresh_breakdown] = 1.5
            signal_priority[bearish_drift & (~fresh_breakdown)] = 5.0

            selection_mask = (
                df["percentage_from_sma"].abs() <= max_distance
            ) | fresh_breakout | fresh_breakdown | trigger_watch | failed_breakout

            filtered_df = df.loc[selection_mask].copy()

            if filtered_df.empty:
                return None

            filtered_df.insert(0, "rank_priority", signal_priority[filtered_df.index])
            filtered_df = filtered_df.sort_values(
                by=["rank_priority", "breakout_confidence", "percentage_from_sma", "symbol"],
                ascending=[True, False, True, True]
            )
            filtered_df = filtered_df.drop(columns=["rank_priority"])

            return filtered_df.reset_index(drop=True)

        except Exception as e:
            self._log(f"Error getting stocks near SMA breakout: {e}")
            return None

    def get_stocks_above_sma(self, sma_period: int = 20, max_distance: float = None) -> Optional[pd.DataFrame]:
        """
        Get stocks currently trading above their SMA (legacy method for compatibility).

        Args:
            sma_period (int): SMA period (20 or 50)
            max_distance (float): Maximum percentage above SMA (None for no limit)

        Returns:
            Optional[pd.DataFrame]: Stocks above SMA or None
        """
        try:
            sma_column = f"sma_{sma_period}"

            # Build query with optional distance filter
            distance_filter = ""
            params = []
            if max_distance is not None:
                distance_filter = f"AND ((p.close - i.{sma_column}) / i.{sma_column} * 100) <= ?"
                params.append(max_distance)

            query = f"""
            SELECT
                p.symbol,
                p.date,
                p.close,
                i.{sma_column},
                i.sma_20,
                i.sma_50,
                i.rsi_14,
                CASE
                    WHEN i.{sma_column} IS NOT NULL AND i.{sma_column} != 0
                        THEN ((p.close - i.{sma_column}) / i.{sma_column} * 100)
                END as percentage_above_sma,
                CASE
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_20 > i.sma_50 THEN 'Bullish Bias'
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_20 < i.sma_50 THEN 'Bearish Bias'
                    ELSE 'Neutral Bias'
                END AS trend_bias,
                CASE
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_50 != 0
                        THEN ROUND(((i.sma_20 - i.sma_50) / i.sma_50) * 100, 2)
                END AS trend_strength,
                CASE
                    WHEN i.rsi_14 >= 60 THEN 'Overbought'
                    WHEN i.rsi_14 <= 40 THEN 'Oversold'
                    WHEN i.rsi_14 IS NULL THEN 'No Signal'
                    ELSE 'Neutral'
                END AS rsi_signal
            FROM {self.price_table} p
            JOIN {self.indicators_table} i ON p.symbol = i.symbol AND p.date = i.date
            WHERE i.{sma_column} IS NOT NULL
                AND i.{sma_column} != 0
                AND p.close > i.{sma_column}
                {distance_filter}
                AND p.date = (
                    SELECT MAX(date) FROM {self.price_table} p2
                    WHERE p2.symbol = p.symbol
                )
            ORDER BY percentage_above_sma ASC
            """

            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df if not df.empty else None

        except Exception as e:
            self._log(f"Error getting stocks above SMA: {e}")
            return None
    
    def get_open_high_patterns(self) -> Optional[pd.DataFrame]:
        """
        Get stocks with open=high patterns.

        Returns:
            Optional[pd.DataFrame]: Stocks with patterns or None
        """
        try:
            query = f"""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) as latest_date
                FROM {self.price_table}
                GROUP BY symbol
            ),
            yesterday_data AS (
                SELECT 
                    p.symbol,
                    p.date as yesterday_date,
                    p.open as yesterday_open,
                    p.high as yesterday_high,
                    p.close as yesterday_close
                FROM {self.price_table} p
                JOIN latest_dates ld ON p.symbol = ld.symbol
                WHERE p.date = date(ld.latest_date, '-1 day')
                    AND ABS(p.open - p.high) < (p.high * 0.001)  -- open ≈ high
            ),
            today_data AS (
                SELECT 
                    p.symbol,
                    p.date as today_date,
                    p.open as today_open,
                    p.high as today_high,
                    p.close as today_close
                FROM {self.price_table} p
                JOIN latest_dates ld ON p.symbol = ld.symbol AND p.date = ld.latest_date
            )
            SELECT
                y.symbol,
                y.yesterday_date,
                y.yesterday_open,
                y.yesterday_high,
                t.today_date,
                t.today_close,
                ((t.today_close - y.yesterday_high) / y.yesterday_high * 100) as breakout_percentage,
                i.sma_20,
                i.sma_50,
                i.rsi_14,
                CASE
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_20 > i.sma_50 THEN 'Bullish Bias'
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_20 < i.sma_50 THEN 'Bearish Bias'
                    ELSE 'Neutral Bias'
                END AS trend_bias,
                CASE
                    WHEN i.sma_20 IS NOT NULL AND i.sma_50 IS NOT NULL AND i.sma_50 != 0
                        THEN ROUND(((i.sma_20 - i.sma_50) / i.sma_50) * 100, 2)
                END AS trend_strength,
                CASE
                    WHEN i.rsi_14 >= 60 THEN 'Overbought'
                    WHEN i.rsi_14 <= 40 THEN 'Oversold'
                    WHEN i.rsi_14 IS NULL THEN 'No Signal'
                    ELSE 'Neutral'
                END AS rsi_signal
            FROM yesterday_data y
            JOIN today_data t ON y.symbol = t.symbol
            LEFT JOIN {self.indicators_table} i ON t.symbol = i.symbol AND t.today_date = i.date
            WHERE t.today_close > y.yesterday_high
            ORDER BY breakout_percentage DESC
            """
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                return df if not df.empty else None
                
        except Exception as e:
            self._log(f"Error getting open=high patterns: {e}")
            return None

    def get_market_health_snapshot(self,
                                   rsi_overbought: float = 60.0,
                                   rsi_oversold: float = 40.0) -> Dict[str, Any]:
        """Summarize the overall market health using the latest stored indicators."""
        try:
            query = f"""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) AS latest_date
                FROM {self.price_table}
                GROUP BY symbol
            ),
            latest_data AS (
                SELECT
                    p.symbol,
                    p.close,
                    p.date,
                    i.sma_20,
                    i.sma_50,
                    i.rsi_14
                FROM {self.price_table} p
                JOIN latest_dates ld ON p.symbol = ld.symbol AND p.date = ld.latest_date
                LEFT JOIN {self.indicators_table} i ON p.symbol = i.symbol AND p.date = i.date
            )
            SELECT
                COUNT(*) AS total_stocks,
                SUM(CASE WHEN sma_20 IS NOT NULL AND close > sma_20 THEN 1 ELSE 0 END) AS above_sma_20,
                SUM(CASE WHEN sma_50 IS NOT NULL AND close > sma_50 THEN 1 ELSE 0 END) AS above_sma_50,
                SUM(CASE WHEN sma_20 IS NOT NULL AND sma_50 IS NOT NULL AND sma_20 > sma_50 THEN 1 ELSE 0 END) AS bullish_trend,
                SUM(CASE WHEN sma_20 IS NOT NULL AND sma_50 IS NOT NULL AND sma_20 < sma_50 THEN 1 ELSE 0 END) AS bearish_trend,
                SUM(CASE WHEN rsi_14 IS NOT NULL AND rsi_14 >= ? THEN 1 ELSE 0 END) AS rsi_overbought,
                SUM(CASE WHEN rsi_14 IS NOT NULL AND rsi_14 <= ? THEN 1 ELSE 0 END) AS rsi_oversold,
                AVG(rsi_14) AS avg_rsi,
                AVG(
                    CASE
                        WHEN sma_20 IS NOT NULL AND sma_50 IS NOT NULL AND sma_50 != 0
                            THEN ((sma_20 - sma_50) / sma_50) * 100
                    END
                ) AS avg_trend_strength
            FROM latest_data
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (rsi_overbought, rsi_oversold))
                row = cursor.fetchone()

                if not row:
                    return {}

                total = int(row[0]) if row[0] is not None else 0
                above_sma_20 = int(row[1]) if row[1] is not None else 0
                above_sma_50 = int(row[2]) if row[2] is not None else 0
                bullish = int(row[3]) if row[3] is not None else 0
                bearish = int(row[4]) if row[4] is not None else 0
                overbought = int(row[5]) if row[5] is not None else 0
                oversold = int(row[6]) if row[6] is not None else 0
                avg_rsi = float(row[7]) if row[7] is not None else None
                avg_trend_strength = float(row[8]) if row[8] is not None else None

                neutral_trend = max(total - bullish - bearish, 0)

                return {
                    'total_stocks': total,
                    'above_sma_20': above_sma_20,
                    'above_sma_50': above_sma_50,
                    'bullish_trend': bullish,
                    'bearish_trend': bearish,
                    'neutral_trend': neutral_trend,
                    'rsi_overbought': overbought,
                    'rsi_oversold': oversold,
                    'avg_rsi': avg_rsi,
                    'avg_trend_strength': avg_trend_strength
                }

        except Exception as e:
            self._log(f"Error generating market health snapshot: {e}")
            return {}

    def count_total_stocks_with_data(self) -> int:
        """Count distinct symbols that have recent price data stored."""
        try:
            query = f"""
            WITH latest_prices AS (
                SELECT symbol, MAX(date) AS latest_date
                FROM {self.price_table}
                GROUP BY symbol
            )
            SELECT COUNT(*) as symbol_count
            FROM latest_prices
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0

        except Exception as e:
            self._log(f"Error counting stocks with data: {e}")
            return 0

    def count_stocks_above_sma(self, sma_period: int = 20, max_distance: float = None) -> int:
        """Count stocks trading above the specified SMA using the latest data."""
        try:
            sma_column = f"sma_{sma_period}"

            distance_filter = ""
            params = []
            if max_distance is not None:
                distance_filter = f"AND ((p.close - i.{sma_column}) / i.{sma_column} * 100) <= ?"
                params.append(max_distance)

            query = f"""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) AS latest_date
                FROM {self.price_table}
                GROUP BY symbol
            )
            SELECT COUNT(DISTINCT p.symbol) as stock_count
            FROM {self.price_table} p
            JOIN latest_dates ld ON p.symbol = ld.symbol AND p.date = ld.latest_date
            JOIN {self.indicators_table} i ON p.symbol = i.symbol AND p.date = i.date
            WHERE i.{sma_column} IS NOT NULL
                AND i.{sma_column} != 0
                AND p.close > i.{sma_column}
                {distance_filter}
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0

        except Exception as e:
            self._log(f"Error counting stocks above SMA: {e}")
            return 0

    def count_open_high_patterns(self) -> int:
        """Count stocks exhibiting the open=high breakout pattern."""
        try:
            query = f"""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) as latest_date
                FROM {self.price_table}
                GROUP BY symbol
            ),
            yesterday_data AS (
                SELECT
                    p.symbol,
                    p.date as yesterday_date,
                    p.open as yesterday_open,
                    p.high as yesterday_high
                FROM {self.price_table} p
                JOIN latest_dates ld ON p.symbol = ld.symbol
                WHERE p.date = date(ld.latest_date, '-1 day')
                    AND ABS(p.open - p.high) < (p.high * 0.001)
            ),
            today_data AS (
                SELECT
                    p.symbol,
                    p.date as today_date,
                    p.open as today_open,
                    p.high as today_high,
                    p.close as today_close
                FROM {self.price_table} p
                JOIN latest_dates ld ON p.symbol = ld.symbol AND p.date = ld.latest_date
            ),
            breakout_patterns AS (
                SELECT
                    y.symbol,
                    y.yesterday_high,
                    t.today_close
                FROM yesterday_data y
                JOIN today_data t ON y.symbol = t.symbol
                WHERE t.today_close > y.yesterday_high
            )
            SELECT COUNT(DISTINCT symbol) as pattern_count
            FROM breakout_patterns
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0

        except Exception as e:
            self._log(f"Error counting open=high patterns: {e}")
            return 0
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """
        Clean up old price and indicator data.
        
        Args:
            days_to_keep (int): Number of days of data to keep
            
        Returns:
            bool: True if successful
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime(DATE_FORMAT)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old price data
                cursor.execute(f"DELETE FROM {self.price_table} WHERE date < ?", (cutoff_date,))
                price_deleted = cursor.rowcount
                
                # Delete old indicator data
                cursor.execute(f"DELETE FROM {self.indicators_table} WHERE date < ?", (cutoff_date,))
                indicator_deleted = cursor.rowcount
                
                conn.commit()
                
                self._log(f"Cleaned up {price_deleted} price records and {indicator_deleted} indicator records older than {days_to_keep} days")
                return True
                
        except Exception as e:
            self._log(f"Error cleaning up old data: {e}")
            return False
