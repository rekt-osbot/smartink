"""
Stock data manager for handling OHLCV data storage and retrieval.
This module extends the database schema to include price and volume data.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from database_manager import DatabaseManager
from utils import print_step
from config import DB_FILE, DATE_FORMAT


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
        Insert OHLCV data into the price table.
        
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
                # Use INSERT OR REPLACE to handle duplicates
                df_to_insert.to_sql(
                    self.price_table,
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                
                conn.commit()
                self._log(f"Inserted {len(df_to_insert)} price records")
                return True
                
        except Exception as e:
            self._log(f"Error inserting price data: {e}")
            return False
    
    def insert_indicators_data(self, data: pd.DataFrame) -> bool:
        """
        Insert technical indicators data.
        
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
                df_to_insert.to_sql(
                    self.indicators_table,
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                
                conn.commit()
                self._log(f"Inserted {len(df_to_insert)} indicator records")
                return True
                
        except Exception as e:
            self._log(f"Error inserting indicators data: {e}")
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
    
    def get_stocks_above_sma(self, sma_period: int = 20) -> Optional[pd.DataFrame]:
        """
        Get stocks currently trading above their SMA.
        
        Args:
            sma_period (int): SMA period (20 or 50)
            
        Returns:
            Optional[pd.DataFrame]: Stocks above SMA or None
        """
        try:
            sma_column = f"sma_{sma_period}"
            
            query = f"""
            SELECT 
                p.symbol,
                p.date,
                p.close,
                i.{sma_column},
                ((p.close - i.{sma_column}) / i.{sma_column} * 100) as percentage_above_sma
            FROM {self.price_table} p
            JOIN {self.indicators_table} i ON p.symbol = i.symbol AND p.date = i.date
            WHERE i.{sma_column} IS NOT NULL 
                AND p.close > i.{sma_column}
                AND p.date = (
                    SELECT MAX(date) FROM {self.price_table} p2 
                    WHERE p2.symbol = p.symbol
                )
            ORDER BY percentage_above_sma DESC
            """
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
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
                ((t.today_close - y.yesterday_high) / y.yesterday_high * 100) as breakout_percentage
            FROM yesterday_data y
            JOIN today_data t ON y.symbol = t.symbol
            WHERE t.today_close > y.yesterday_high
            ORDER BY breakout_percentage DESC
            """
            
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                return df if not df.empty else None
                
        except Exception as e:
            self._log(f"Error getting open=high patterns: {e}")
            return None
    
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
