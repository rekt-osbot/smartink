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
from optimized_stock_filter import OptimizedStockFilter, PostFetchFilter
from stock_filter_cache import CachedStockFilter


class StockDataFetcher:
    """Handles fetching and processing stock data from yfinance."""
    
    def __init__(self, verbose: bool = True, use_filtering: bool = True):
        """
        Initialize the stock data fetcher.

        Args:
            verbose (bool): Whether to print detailed logs
            use_filtering (bool): Whether to apply stock filtering for optimization
        """
        self.verbose = verbose
        self.use_filtering = use_filtering
        self.db_manager = DatabaseManager(verbose=verbose)

        # Initialize cached stock filter if enabled
        if self.use_filtering:
            self.cached_filter = CachedStockFilter(
                min_market_cap_cr=100.0,  # 100 crores minimum market cap
                min_daily_value_l=10.0,   # 10 lakhs minimum daily trading value
                verbose=verbose
            )
            self.post_filter = PostFetchFilter(
                min_market_cap_cr=100.0,  # 100 crores (for future use)
                min_daily_value_l=10.0    # 10 lakhs minimum daily trading value
            )
    
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
    
    def fetch_multiple_stocks_bulk(self, symbols: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks using yfinance bulk download for better performance.

        Args:
            symbols (List[str]): List of stock symbols
            period (str): Period for data

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
        """
        results = {}
        total_symbols = len(symbols)

        self._log(f"Fetching data for {total_symbols} stocks using bulk download...")

        # Process in batches for better performance and memory management
        batch_size = 100  # Larger batches for bulk download

        for batch_start in range(0, total_symbols, batch_size):
            batch_end = min(batch_start + batch_size, total_symbols)
            batch_symbols = symbols[batch_start:batch_end]

            self._log(f"Processing batch {batch_start//batch_size + 1}: symbols {batch_start+1}-{batch_end}")

            try:
                # Convert symbols to yfinance format
                yf_symbols = [self.get_nse_symbol_for_yfinance(symbol) for symbol in batch_symbols]

                # Bulk download using yfinance
                bulk_data = yf.download(
                    yf_symbols,
                    period=period,
                    group_by='ticker',
                    auto_adjust=True,
                    prepost=True,
                    threads=True,
                    progress=False
                )

                if bulk_data.empty:
                    self._log(f"No data returned for batch {batch_start//batch_size + 1}")
                    continue

                # Process each stock from bulk data
                for i, symbol in enumerate(batch_symbols):
                    yf_symbol = yf_symbols[i]

                    try:
                        if len(batch_symbols) == 1:
                            # Single stock - data is not multi-indexed
                            stock_data = bulk_data
                        else:
                            # Multiple stocks - extract data for this symbol
                            if yf_symbol in bulk_data.columns.levels[0]:
                                stock_data = bulk_data[yf_symbol]
                            else:
                                self._log(f"No data for {symbol} ({yf_symbol})")
                                continue

                        # Check if we have valid data
                        if stock_data.empty or len(stock_data) < 5:
                            self._log(f"Insufficient data for {symbol}")
                            continue

                        # Reset index to make Date a column
                        stock_data = stock_data.reset_index()

                        # Rename columns to match our convention
                        stock_data.rename(columns={
                            'Date': 'date',
                            'Open': 'open',
                            'High': 'high',
                            'Low': 'low',
                            'Close': 'close',
                            'Volume': 'volume'
                        }, inplace=True)

                        # Add symbol column
                        stock_data['symbol'] = symbol

                        # Select only the columns we need
                        required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                        if all(col in stock_data.columns for col in required_columns):
                            stock_data = stock_data[required_columns]

                            # Calculate 20-day SMA
                            stock_data = self.calculate_sma(stock_data, 20)
                            results[symbol] = stock_data

                            self._log(f"✓ Processed {symbol}: {len(stock_data)} records")
                        else:
                            self._log(f"Missing required columns for {symbol}")

                    except Exception as e:
                        self._log(f"Error processing {symbol}: {e}")
                        continue

            except Exception as e:
                self._log(f"Error in bulk download for batch {batch_start//batch_size + 1}: {e}")
                # Fallback to individual downloads for this batch
                self._log("Falling back to individual downloads...")
                for symbol in batch_symbols:
                    data = self.fetch_stock_data(symbol, period)
                    if data is not None:
                        data = self.calculate_sma(data, 20)
                        results[symbol] = data
                    time.sleep(0.1)  # Rate limiting for fallback

            # Pause between batches
            if batch_end < total_symbols:
                self._log(f"Batch completed. Pausing before next batch...")
                time.sleep(2)  # 2 second pause between batches

        self._log(f"Bulk fetch completed: {len(results)} successful out of {total_symbols} stocks")
        return results

    def fetch_multiple_stocks(self, symbols: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks with automatic fallback between bulk and individual methods.

        Args:
            symbols (List[str]): List of stock symbols
            period (str): Period for data

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
        """
        # Try bulk download first for better performance
        if len(symbols) > 10:
            self._log("Using bulk download method for better performance...")
            return self.fetch_multiple_stocks_bulk(symbols, period)
        else:
            # For small numbers, individual downloads might be more reliable
            self._log("Using individual download method...")
            return self.fetch_multiple_stocks_individual(symbols, period)

    def fetch_multiple_stocks_individual(self, symbols: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks individually (fallback method).

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

        self._log(f"Fetching data for {total_symbols} stocks individually...")

        for i, symbol in enumerate(symbols, 1):
            self._log(f"Progress: {i}/{total_symbols} - {symbol}")

            data = self.fetch_stock_data(symbol, period)
            if data is not None:
                # Calculate 20-day SMA
                data = self.calculate_sma(data, 20)
                results[symbol] = data
                successful_fetches += 1
            else:
                failed_fetches += 1

            # Rate limiting - pause between requests
            if i < total_symbols:
                time.sleep(0.1)  # 100ms delay between requests

        self._log(f"Individual fetch completed: {successful_fetches} successful, {failed_fetches} failed out of {total_symbols} stocks")
        return results

    def get_comprehensive_nse_stocks(self) -> List[str]:
        """
        Get a comprehensive list of NSE stocks for cloud deployment.
        This includes popular stocks plus additional liquid stocks.

        Returns:
            List[str]: Comprehensive list of NSE stock symbols
        """
        # Start with popular stocks
        comprehensive_stocks = self.get_popular_nse_stocks().copy()

        # Add more liquid and well-known NSE stocks
        additional_stocks = [
            # Banking & Financial Services
            'BANKBARODA', 'CANFINHOME', 'CHOLAFIN', 'FEDERALBNK', 'IDFCFIRSTB',
            'PNB', 'RBLBANK', 'YESBANK', 'BAJAJHLDNG', 'MUTHOOTFIN',

            # IT & Technology
            'MINDTREE', 'MPHASIS', 'PERSISTENT', 'LTTS', 'COFORGE',

            # Pharmaceuticals
            'BIOCON', 'CADILAHC', 'GLENMARK', 'LUPIN', 'TORNTPHARM',
            'ALKEM', 'AUROPHARMA', 'ZYDUSLIFE',

            # Consumer Goods
            'DABUR', 'MARICO', 'COLPAL', 'EMAMILTD', 'GODREJIND',
            'JUBLFOOD', 'TATACONSUM', 'VBL',

            # Automobiles
            'ASHOKLEY', 'BAJAJ-AUTO', 'ESCORTS', 'MAHINDRA', 'MOTHERSON',
            'TVSMOTOR', 'BOSCHLTD', 'EXIDEIND',

            # Metals & Mining
            'VEDL', 'NMDC', 'SAIL', 'JINDALSTEL', 'RATNAMANI',
            'WELCORP', 'MOIL', 'NATIONALUM',

            # Energy & Utilities
            'ADANIGREEN', 'ADANITRANS', 'GAIL', 'IOC', 'RELIANCE',
            'TATAPOWER', 'TORNTPOWER', 'NHPC',

            # Telecom
            'IDEA', 'INDUSINDBK',

            # Cement
            'ACC', 'AMBUJACEMENT', 'RAMCOCEM', 'JKCEMENT',

            # Textiles
            'ARVIND', 'RAYMOND', 'WELSPUNIND',

            # Infrastructure
            'IRCTC', 'CONCOR', 'GMRINFRA', 'L&TFH',

            # Chemicals
            'AAVAS', 'DEEPAKNTR', 'GNFC', 'PIDILITIND',

            # Others
            'DIXON', 'POLYCAB', 'CROMPTON', 'HAVELLS', 'VOLTAS'
        ]

        # Add additional stocks, avoiding duplicates
        for stock in additional_stocks:
            if stock not in comprehensive_stocks:
                comprehensive_stocks.append(stock)

        self._log(f"Generated comprehensive stock list with {len(comprehensive_stocks)} symbols")
        return comprehensive_stocks

    def get_stocks_from_database(self, use_popular_only: bool = False, apply_filters: bool = None) -> List[str]:
        """
        Get list of stock symbols from the database with cloud-friendly fallbacks.

        Args:
            use_popular_only (bool): If True, filter to only popular stocks
            apply_filters (bool): If True, apply stock filtering. If None, uses instance setting.

        Returns:
            List[str]: List of stock symbols
        """
        # Determine if filtering should be applied
        if apply_filters is None:
            apply_filters = self.use_filtering

        try:
            if use_popular_only:
                # Get popular stocks that exist in our database
                popular = self.get_popular_nse_stocks()
                query = f"SELECT DISTINCT symbol FROM tradable_stocks WHERE symbol IN ({','.join(['?' for _ in popular])}) ORDER BY symbol"
                result = self.db_manager.execute_query(query, popular)
            else:
                if apply_filters and hasattr(self, 'cached_filter'):
                    # Use cached filtering for best performance
                    self._log("Applying cached stock filtering...")
                    filtered_symbols = self.cached_filter.get_filtered_stocks()
                    self._log(f"Found {len(filtered_symbols)} cached filtered stocks")
                    return filtered_symbols
                else:
                    # Get all stocks without filtering
                    query = "SELECT DISTINCT symbol FROM tradable_stocks ORDER BY symbol"
                    result = self.db_manager.execute_query(query)

            if result and result[1]:
                symbols = [row[0] for row in result[1]]
                self._log(f"Found {len(symbols)} stocks in database")
                return symbols
            else:
                self._log("No stocks found in database, using fallback stock list")
                # Cloud-friendly fallback
                if use_popular_only:
                    return self.get_popular_nse_stocks()
                else:
                    return self.get_comprehensive_nse_stocks()

        except Exception as e:
            self._log(f"Error getting stocks from database: {e}")
            self._log("Using fallback stock list")
            # Cloud-friendly fallback
            if use_popular_only:
                return self.get_popular_nse_stocks()
            else:
                return self.get_comprehensive_nse_stocks()

    def get_filtering_summary(self) -> Dict[str, int]:
        """
        Get summary of stock filtering performance.

        Returns:
            Dictionary with filtering statistics
        """
        if not self.use_filtering or not hasattr(self, 'cached_filter'):
            return {"filtering_enabled": False}

        try:
            cache_status = self.cached_filter.get_cache_status()
            summary = {
                "filtering_enabled": True,
                "optimization_type": "cached_filtering",
                "cache_current": cache_status.get("current", False),
                "cache_date": cache_status.get("date"),
                "cached_stock_count": cache_status.get("count", 0),
                "cache_age_days": cache_status.get("age_days", 0),
                "processing_time_seconds": cache_status.get("processing_time_seconds")
            }
            return summary
        except Exception as e:
            self._log(f"Error getting filtering summary: {e}")
            return {"filtering_enabled": False, "error": str(e)}

    def toggle_filtering(self, enabled: bool):
        """
        Enable or disable stock filtering.

        Args:
            enabled (bool): Whether to enable filtering
        """
        self.use_filtering = enabled
        if enabled and not hasattr(self, 'cached_filter'):
            self.cached_filter = CachedStockFilter(
                min_market_cap_cr=100.0,
                min_daily_value_l=10.0,
                verbose=self.verbose
            )
            self.post_filter = PostFetchFilter(
                min_market_cap_cr=100.0,
                min_daily_value_l=10.0
            )
        self._log(f"Cached stock filtering {'enabled' if enabled else 'disabled'}")

    def get_unfiltered_stocks_from_database(self) -> List[str]:
        """
        Get all stocks from database without any filtering (for comparison/debugging).

        Returns:
            List[str]: All stock symbols from database
        """
        return self.get_stocks_from_database(use_popular_only=False, apply_filters=False)

    def apply_post_fetch_filtering(self, stock_data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Apply post-fetch filtering to already downloaded stock data.
        This eliminates low-volume stocks using the data we already have.

        Args:
            stock_data_dict: Dictionary mapping symbols to their OHLCV DataFrames

        Returns:
            Filtered dictionary with only stocks meeting criteria
        """
        if not self.use_filtering or not hasattr(self, 'post_filter'):
            return stock_data_dict

        self._log("Applying post-fetch volume filtering...")
        filtered_data = self.post_filter.filter_by_volume(stock_data_dict)

        filtered_out = len(stock_data_dict) - len(filtered_data)
        if filtered_out > 0:
            self._log(f"Post-fetch filter: {filtered_out} low-volume stocks filtered out")

        return filtered_data

    def refresh_filter_cache(self) -> List[str]:
        """
        Force refresh the filter cache (expensive operation).
        Use this at the start of trading day to get fresh master list.

        Returns:
            List of freshly filtered stock symbols
        """
        if not self.use_filtering or not hasattr(self, 'cached_filter'):
            self._log("Filtering not enabled - cannot refresh cache")
            return []

        self._log("Force refreshing filter cache (this may take a while)...")
        return self.cached_filter.refresh_cache()

    def get_filter_cache_status(self) -> Dict:
        """
        Get detailed cache status information.

        Returns:
            Dictionary with cache status details
        """
        if not self.use_filtering or not hasattr(self, 'cached_filter'):
            return {"filtering_enabled": False}

        return self.cached_filter.get_cache_status()

    def clear_filter_cache(self) -> bool:
        """
        Clear the filter cache.

        Returns:
            True if cleared successfully
        """
        if not self.use_filtering or not hasattr(self, 'cached_filter'):
            return False

        return self.cached_filter.clear_cache()
