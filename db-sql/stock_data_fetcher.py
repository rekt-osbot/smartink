"""
Stock data fetcher module for retrieving OHLCV data from yfinance.
This module handles fetching real-time and historical stock data for technical analysis.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time

from utils import print_step
from database_manager import DatabaseManager


class StockDataFetcher:
    """Handles fetching and processing stock data from yfinance."""
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the stock data fetcher.
        
        Args:
            verbose (bool): Whether to print detailed logs
        """
        self.verbose = verbose
        self.db_manager = DatabaseManager(verbose=verbose)
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def get_nse_symbol_for_yfinance(self, symbol: str) -> str:
        """
        Convert NSE symbol to yfinance format.

        Args:
            symbol (str): NSE symbol

        Returns:
            str: yfinance compatible symbol
        """
        # For NSE stocks, append .NS suffix
        if not symbol.endswith('.NS'):
            return f"{symbol}.NS"
        return symbol

    def get_popular_nse_stocks(self) -> List[str]:
        """
        Get a list of popular NSE stocks that are likely to have data on yfinance.

        Returns:
            List[str]: List of popular stock symbols
        """
        # Popular NSE stocks that are definitely available on yfinance
        popular_stocks = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK',
            'KOTAKBANK', 'BHARTIARTL', 'ITC', 'SBIN', 'BAJFINANCE', 'ASIANPAINT',
            'MARUTI', 'AXISBANK', 'LT', 'TITAN', 'NESTLEIND', 'ULTRACEMCO',
            'WIPRO', 'ONGC', 'TECHM', 'SUNPHARMA', 'POWERGRID', 'NTPC',
            'COALINDIA', 'TATAMOTORS', 'BAJAJFINSV', 'HCLTECH', 'DRREDDY',
            'BRITANNIA', 'EICHERMOT', 'ADANIPORTS', 'JSWSTEEL', 'GRASIM',
            'CIPLA', 'TATASTEEL', 'BPCL', 'HEROMOTOCO', 'DIVISLAB', 'INDUSINDBK',
            'ADANIENT', 'APOLLOHOSP', 'TATACONSUM', 'BAJAJ-AUTO', 'HINDALCO',
            'SHREECEM', 'UPL', 'SBILIFE', 'HDFCLIFE', 'PIDILITIND'
        ]
        return popular_stocks
    
    def generate_mock_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """
        Generate mock OHLCV data for demonstration when Yahoo Finance is not available.

        Args:
            symbol (str): Stock symbol
            days (int): Number of days of data to generate

        Returns:
            pd.DataFrame: Mock OHLCV data
        """
        import random
        from datetime import datetime, timedelta

        # Base price varies by stock
        base_prices = {
            'RELIANCE': 2500, 'TCS': 3500, 'HDFCBANK': 1600, 'INFY': 1400, 'HINDUNILVR': 2400,
            'ICICIBANK': 1000, 'KOTAKBANK': 1800, 'BHARTIARTL': 900, 'ITC': 450, 'SBIN': 600,
            'BAJFINANCE': 7000, 'ASIANPAINT': 3200, 'MARUTI': 10000, 'AXISBANK': 1100, 'LT': 3500
        }

        base_price = base_prices.get(symbol, 1000)

        dates = []
        data_rows = []

        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            # Skip weekends
            if date.weekday() >= 5:
                continue

            # Generate realistic OHLCV data
            daily_change = random.uniform(-0.05, 0.05)  # ±5% daily change
            close = base_price * (1 + daily_change)

            high = close * random.uniform(1.0, 1.03)
            low = close * random.uniform(0.97, 1.0)
            open_price = low + (high - low) * random.random()
            volume = random.randint(100000, 10000000)

            data_rows.append({
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })

            base_price = close  # Use previous close as next base

        return pd.DataFrame(data_rows)

    def fetch_stock_data(self, symbol: str, period: str = "3mo") -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a single stock with robust error handling.

        Args:
            symbol (str): Stock symbol
            period (str): Period for data (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Optional[pd.DataFrame]: OHLCV data or None if failed
        """
        try:
            yf_symbol = self.get_nse_symbol_for_yfinance(symbol)
            self._log(f"Fetching data for {yf_symbol}...")

            # Create ticker and fetch data
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(period=period)

            if data.empty:
                self._log(f"No data found for {yf_symbol}")
                return None

            # Validate data quality
            if len(data) < 5:  # Need at least 5 days for meaningful analysis
                self._log(f"Insufficient data for {symbol}: only {len(data)} records")
                return None

            if data.empty:
                # Try without .NS suffix for some stocks
                if yf_symbol.endswith('.NS'):
                    alt_symbol = symbol  # Try without .NS
                    ticker_alt = yf.Ticker(alt_symbol)
                    data = ticker_alt.history(period=period, timeout=10, raise_errors=False)
                    if not data.empty:
                        yf_symbol = alt_symbol

                if data.empty:
                    return None

            # Validate data quality
            if len(data) < 5:  # Need at least 5 days for meaningful analysis
                return None

            # Reset index to make Date a column
            data.reset_index(inplace=True)

            # Add symbol column
            data['Symbol'] = symbol

            # Rename columns to match our convention
            data.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Symbol': 'symbol'
            }, inplace=True)

            # Select only the columns we need and ensure they exist
            required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_columns):
                return None

            data = data[required_columns]

            # Validate numeric data
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if data[col].isna().all():
                    return None

            self._log(f"✓ Fetched {len(data)} records for {symbol}")
            return data

        except Exception as e:
            # Silently handle errors - this is expected for many stocks
            return None
    
    def calculate_sma(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Calculate Simple Moving Average for the close price.
        
        Args:
            data (pd.DataFrame): OHLCV data
            window (int): SMA window period
            
        Returns:
            pd.DataFrame: Data with SMA column added
        """
        if len(data) < window:
            self._log(f"Not enough data for {window}-day SMA calculation")
            data[f'sma_{window}'] = np.nan
            return data
        
        # Sort by date to ensure proper SMA calculation
        data = data.sort_values('date').copy()
        
        # Calculate SMA
        data[f'sma_{window}'] = data['close'].rolling(window=window, min_periods=window).mean()
        
        return data
    
    def fetch_multiple_stocks(self, symbols: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks with rate limiting and progress tracking.

        Args:
            symbols (List[str]): List of stock symbols
            period (str): Period for data

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
        """
        results = {}
        total_symbols = len(symbols)
        successful_fetches = 0
        failed_fetches = 0

        self._log(f"Fetching data for {total_symbols} stocks...")

        # Process in batches for better performance
        batch_size = 50
        for batch_start in range(0, total_symbols, batch_size):
            batch_end = min(batch_start + batch_size, total_symbols)
            batch_symbols = symbols[batch_start:batch_end]

            self._log(f"Processing batch {batch_start//batch_size + 1}: symbols {batch_start+1}-{batch_end}")

            for i, symbol in enumerate(batch_symbols):
                overall_progress = batch_start + i + 1
                self._log(f"Progress: {overall_progress}/{total_symbols} - {symbol}")

                data = self.fetch_stock_data(symbol, period)
                if data is not None:
                    # Calculate 20-day SMA
                    data = self.calculate_sma(data, 20)
                    results[symbol] = data
                    successful_fetches += 1
                else:
                    failed_fetches += 1

                # Rate limiting - pause between requests
                if overall_progress < total_symbols:
                    time.sleep(0.05)  # 50ms delay between requests for faster processing

            # Longer pause between batches
            if batch_end < total_symbols:
                self._log(f"Batch completed. Pausing before next batch...")
                time.sleep(1)  # 1 second pause between batches

        self._log(f"Fetch completed: {successful_fetches} successful, {failed_fetches} failed out of {total_symbols} stocks")
        return results
    
    def get_popular_nse_stocks(self) -> List[str]:
        """
        Get a curated list of popular NSE stocks that work well with yfinance.

        Returns:
            List[str]: List of popular stock symbols
        """
        # Popular NSE stocks that are definitely available on yfinance
        popular_stocks = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK',
            'KOTAKBANK', 'BHARTIARTL', 'ITC', 'SBIN', 'BAJFINANCE', 'ASIANPAINT',
            'MARUTI', 'AXISBANK', 'LT', 'TITAN', 'NESTLEIND', 'ULTRACEMCO',
            'WIPRO', 'ONGC', 'TECHM', 'SUNPHARMA', 'POWERGRID', 'NTPC',
            'COALINDIA', 'TATAMOTORS', 'BAJAJFINSV', 'HCLTECH', 'DRREDDY',
            'BRITANNIA', 'EICHERMOT', 'ADANIPORTS', 'JSWSTEEL', 'GRASIM',
            'CIPLA', 'TATASTEEL', 'BPCL', 'HEROMOTOCO', 'DIVISLAB', 'INDUSINDBK',
            'ADANIENT', 'APOLLOHOSP', 'TATACONSUM', 'HINDALCO', 'SHREECEM',
            'UPL', 'SBILIFE', 'HDFCLIFE', 'PIDILITIND', 'GODREJCP'
        ]
        return popular_stocks

    def get_stocks_from_database(self, use_popular_only: bool = False) -> List[str]:
        """
        Get list of stock symbols from the database.

        Args:
            use_popular_only (bool): If True, filter to only popular stocks

        Returns:
            List[str]: List of stock symbols
        """
        try:
            if use_popular_only:
                # Get popular stocks that exist in our database
                popular = self.get_popular_nse_stocks()
                query = f"SELECT DISTINCT symbol FROM tradable_stocks WHERE symbol IN ({','.join(['?' for _ in popular])}) ORDER BY symbol"
                result = self.db_manager.execute_query(query, popular)
            else:
                query = "SELECT DISTINCT symbol FROM tradable_stocks ORDER BY symbol"
                result = self.db_manager.execute_query(query)

            if result and result[1]:
                symbols = [row[0] for row in result[1]]
                self._log(f"Found {len(symbols)} stocks in database")
                return symbols
            else:
                self._log("No stocks found in database")
                return []

        except Exception as e:
            self._log(f"Error getting stocks from database: {e}")
            return []
    
    def identify_stocks_above_sma(self, stock_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Identify stocks trading above their 20-day SMA.
        
        Args:
            stock_data (Dict[str, pd.DataFrame]): Stock data dictionary
            
        Returns:
            List[Dict]: List of stocks above SMA with details
        """
        stocks_above_sma = []
        
        for symbol, data in stock_data.items():
            if data.empty or 'sma_20' not in data.columns:
                continue
            
            # Get the latest data point
            latest = data.iloc[-1]
            
            # Check if current price is above SMA and SMA is not NaN
            if pd.notna(latest['sma_20']) and latest['close'] > latest['sma_20']:
                stocks_above_sma.append({
                    'symbol': symbol,
                    'date': latest['date'],
                    'close': latest['close'],
                    'sma_20': latest['sma_20'],
                    'percentage_above_sma': ((latest['close'] - latest['sma_20']) / latest['sma_20']) * 100
                })
        
        # Sort by percentage above SMA (descending)
        stocks_above_sma.sort(key=lambda x: x['percentage_above_sma'], reverse=True)
        
        self._log(f"Found {len(stocks_above_sma)} stocks above 20-day SMA")
        return stocks_above_sma
    
    def identify_open_high_patterns(self, stock_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Identify stocks with open=high patterns.
        
        Args:
            stock_data (Dict[str, pd.DataFrame]): Stock data dictionary
            
        Returns:
            List[Dict]: List of stocks with open=high patterns
        """
        open_high_patterns = []
        
        for symbol, data in stock_data.items():
            if len(data) < 2:
                continue
            
            # Sort by date
            data = data.sort_values('date')
            
            # Get last two days
            yesterday = data.iloc[-2] if len(data) >= 2 else None
            today = data.iloc[-1]
            
            # Pattern 1: Yesterday open=high, today trading above yesterday's high
            if yesterday is not None:
                yesterday_open_equals_high = abs(yesterday['open'] - yesterday['high']) < (yesterday['high'] * 0.001)  # 0.1% tolerance
                today_above_yesterday_high = today['close'] > yesterday['high']
                
                if yesterday_open_equals_high and today_above_yesterday_high:
                    open_high_patterns.append({
                        'symbol': symbol,
                        'pattern_type': 'yesterday_open_high_today_above',
                        'yesterday_date': yesterday['date'],
                        'yesterday_open': yesterday['open'],
                        'yesterday_high': yesterday['high'],
                        'today_date': today['date'],
                        'today_close': today['close'],
                        'breakout_percentage': ((today['close'] - yesterday['high']) / yesterday['high']) * 100
                    })
            
            # Pattern 2: Today open=high and currently trading above that high
            today_open_equals_high = abs(today['open'] - today['high']) < (today['high'] * 0.001)  # 0.1% tolerance
            today_close_above_high = today['close'] > today['high']
            
            if today_open_equals_high and today_close_above_high:
                open_high_patterns.append({
                    'symbol': symbol,
                    'pattern_type': 'today_open_high_now_above',
                    'today_date': today['date'],
                    'today_open': today['open'],
                    'today_high': today['high'],
                    'current_close': today['close'],
                    'breakout_percentage': ((today['close'] - today['high']) / today['high']) * 100
                })
        
        # Sort by breakout percentage (descending)
        open_high_patterns.sort(key=lambda x: x.get('breakout_percentage', 0), reverse=True)
        
        self._log(f"Found {len(open_high_patterns)} stocks with open=high patterns")
        return open_high_patterns
