"""
Stock filtering utility module for optimizing data processing.
Filters out irrelevant stocks to improve performance and focus on tradeable securities.
"""

import sqlite3
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import time
from database_manager import DatabaseManager
from config import DB_FILE


class StockFilter:
    """
    Comprehensive stock filtering system to optimize data processing.
    
    Filters applied:
    1. Exclude BE (Book Entry) and BZ (Blacklisted/Suspended) categories
    2. Exclude stocks below minimum market cap (default: 100 crores)
    3. Exclude stocks with low trading volume (default: 10L INR daily value)
    4. Focus on liquid, actively traded securities
    """
    
    def __init__(self, 
                 min_market_cap_cr: float = 100.0,  # 100 crores
                 min_daily_value_l: float = 10.0,   # 10 lakhs INR
                 verbose: bool = True):
        """
        Initialize the stock filter.
        
        Args:
            min_market_cap_cr: Minimum market cap in crores (default: 100)
            min_daily_value_l: Minimum daily trading value in lakhs (default: 10)
            verbose: Whether to print detailed information
        """
        self.min_market_cap_cr = min_market_cap_cr
        self.min_daily_value_l = min_daily_value_l
        self.verbose = verbose
        self.db_manager = DatabaseManager(verbose=verbose)
        
        # Cache for filtered stocks to avoid repeated calculations
        self._filtered_stocks_cache = None
        self._cache_timestamp = None
        self._cache_duration_hours = 24  # Cache for 24 hours
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[StockFilter] {message}")
    
    def get_stocks_by_series(self, excluded_series: List[str] = None) -> List[str]:
        """
        Get stocks filtered by series (category).
        
        Args:
            excluded_series: List of series to exclude (default: ['BE', 'BZ'])
            
        Returns:
            List of stock symbols that pass the series filter
        """
        if excluded_series is None:
            excluded_series = ['BE', 'BZ']
        
        try:
            # Build the exclusion condition
            placeholders = ','.join(['?' for _ in excluded_series])
            query = f"""
                SELECT symbol 
                FROM tradable_stocks 
                WHERE series NOT IN ({placeholders})
                ORDER BY symbol
            """
            
            result = self.db_manager.execute_query(query, excluded_series)
            if result and result[1]:
                symbols = [row[0] for row in result[1]]
                self._log(f"Series filter: {len(symbols)} stocks pass (excluded: {excluded_series})")
                return symbols
            else:
                self._log("No stocks found after series filtering")
                return []
                
        except Exception as e:
            self._log(f"Error in series filtering: {e}")
            return []
    
    def get_market_cap_and_volume_data(self, symbols: List[str], sample_size: int = 50) -> Dict[str, Dict]:
        """
        Get market cap and trading volume data efficiently using bulk yfinance calls.

        Args:
            symbols: List of stock symbols
            sample_size: Number of stocks to sample for analysis

        Returns:
            Dictionary mapping symbols to their market cap (crores) and trading volume (lakhs)
        """
        if not symbols:
            return {}

        # Sample stocks to avoid hitting API limits
        sample_symbols = symbols[:sample_size] if len(symbols) > sample_size else symbols
        stock_data = {}

        self._log(f"Fetching market cap and volume data for {len(sample_symbols)} stocks...")

        try:
            # Convert to yfinance format
            yf_symbols = [f"{symbol}.NS" for symbol in sample_symbols]

            # Bulk download for efficiency
            bulk_data = yf.download(
                yf_symbols,
                period="5d",
                group_by='ticker',
                auto_adjust=True,
                prepost=False,
                threads=True,
                progress=False
            )

            if bulk_data.empty:
                self._log("No bulk data returned from yfinance")
                return {}

            # Process each stock
            for i, symbol in enumerate(sample_symbols):
                try:
                    yf_symbol = yf_symbols[i]

                    # Get ticker info for market cap
                    ticker = yf.Ticker(yf_symbol)
                    info = ticker.info

                    # Extract market cap
                    market_cap_inr = info.get('marketCap', 0)
                    market_cap_cr = 0
                    if market_cap_inr and market_cap_inr > 0:
                        market_cap_cr = market_cap_inr / 10_000_000  # Convert to crores

                    # Extract trading volume from historical data
                    avg_trading_value_l = 0
                    if len(yf_symbols) == 1:
                        # Single stock case
                        hist_data = bulk_data
                    else:
                        # Multiple stocks case
                        hist_data = bulk_data[yf_symbol] if yf_symbol in bulk_data.columns.get_level_values(0) else pd.DataFrame()

                    if not hist_data.empty and 'Close' in hist_data.columns and 'Volume' in hist_data.columns:
                        # Calculate average daily trading value
                        hist_data_clean = hist_data.dropna()
                        if len(hist_data_clean) > 0:
                            trading_values = hist_data_clean['Close'] * hist_data_clean['Volume']
                            avg_trading_value = trading_values.mean()
                            if avg_trading_value and avg_trading_value > 0:
                                avg_trading_value_l = avg_trading_value / 100_000  # Convert to lakhs

                    stock_data[symbol] = {
                        'market_cap_cr': market_cap_cr,
                        'avg_trading_value_l': avg_trading_value_l
                    }

                except Exception as e:
                    self._log(f"Error processing data for {symbol}: {e}")
                    continue

        except Exception as e:
            self._log(f"Error in bulk data fetch: {e}")
            return {}

        self._log(f"Successfully fetched data for {len(stock_data)} stocks")
        return stock_data
    
    def get_trading_volume_data(self, symbols: List[str], sample_size: int = 50) -> Dict[str, float]:
        """
        Get recent trading volume data to filter low-volume stocks.
        This method is deprecated - use get_market_cap_and_volume_data for efficiency.

        Args:
            symbols: List of stock symbols
            sample_size: Number of stocks to sample for volume analysis

        Returns:
            Dictionary mapping symbols to average daily trading value in lakhs
        """
        # Use the more efficient combined method
        combined_data = self.get_market_cap_and_volume_data(symbols, sample_size)
        return {symbol: data['avg_trading_value_l'] for symbol, data in combined_data.items()}
    
    def apply_comprehensive_filter(self,
                                 use_market_cap: bool = True,
                                 use_trading_volume: bool = True,
                                 sample_size: int = 100) -> List[str]:
        """
        Apply comprehensive filtering to get optimized stock list.

        Args:
            use_market_cap: Whether to apply market cap filtering
            use_trading_volume: Whether to apply trading volume filtering
            sample_size: Sample size for market data analysis

        Returns:
            List of filtered stock symbols
        """
        self._log("Starting comprehensive stock filtering...")

        # Step 1: Filter by series (exclude BE, BZ)
        stocks_after_series = self.get_stocks_by_series()
        if not stocks_after_series:
            return []

        self._log(f"After series filter: {len(stocks_after_series)} stocks")

        # Step 2: Apply market cap and trading volume filters efficiently
        if use_market_cap or use_trading_volume:
            # Get both market cap and volume data in one efficient call
            combined_data = self.get_market_cap_and_volume_data(stocks_after_series, sample_size)

            if combined_data:
                # Filter based on criteria
                stocks_passing_filters = []

                for symbol, data in combined_data.items():
                    mcap_ok = True
                    volume_ok = True

                    if use_market_cap:
                        mcap_ok = data['market_cap_cr'] >= self.min_market_cap_cr

                    if use_trading_volume:
                        volume_ok = data['avg_trading_value_l'] >= self.min_daily_value_l

                    if mcap_ok and volume_ok:
                        stocks_passing_filters.append(symbol)

                self._log(f"Stocks passing market data filters: {len(stocks_passing_filters)}")

                # For stocks without market data, include them (conservative approach)
                stocks_without_data = [s for s in stocks_after_series if s not in combined_data]
                final_filtered_stocks = stocks_passing_filters + stocks_without_data

                self._log(f"Stocks without market data (included): {len(stocks_without_data)}")
            else:
                final_filtered_stocks = stocks_after_series
        else:
            final_filtered_stocks = stocks_after_series

        # Sort the final list
        final_filtered_stocks.sort()

        self._log(f"Final filtered stock count: {len(final_filtered_stocks)}")
        self._log(f"Reduction: {len(stocks_after_series) - len(final_filtered_stocks)} stocks filtered out")

        return final_filtered_stocks

    def filter_stocks_with_data(self, stock_data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Filter stocks based on their actual fetched data (market cap and volume).
        This is more efficient as it uses data already fetched for analysis.

        Args:
            stock_data_dict: Dictionary mapping symbols to their OHLCV DataFrames

        Returns:
            Filtered dictionary with only stocks meeting criteria
        """
        if not stock_data_dict:
            return {}

        filtered_data = {}
        filtered_count = 0
        volume_filtered = 0

        self._log(f"Filtering {len(stock_data_dict)} stocks based on fetched data...")

        for symbol, data in stock_data_dict.items():
            try:
                if data is None or data.empty:
                    continue

                # Check trading volume criteria
                volume_ok = True
                if 'Volume' in data.columns and 'Close' in data.columns:
                    # Calculate average daily trading value
                    data_clean = data.dropna()
                    if len(data_clean) > 0:
                        trading_values = data_clean['Close'] * data_clean['Volume']
                        avg_trading_value = trading_values.mean()
                        avg_trading_value_l = avg_trading_value / 100_000  # Convert to lakhs

                        if avg_trading_value_l < self.min_daily_value_l:
                            volume_ok = False
                            volume_filtered += 1

                # For market cap, we'd need to fetch it separately or get it from ticker info
                # For now, we'll focus on volume filtering which is more practical with OHLCV data

                if volume_ok:
                    filtered_data[symbol] = data
                else:
                    filtered_count += 1

            except Exception as e:
                self._log(f"Error filtering {symbol}: {e}")
                # Include stock if there's an error (conservative approach)
                filtered_data[symbol] = data

        self._log(f"Filtered out {filtered_count} stocks based on trading volume")
        self._log(f"Remaining stocks: {len(filtered_data)}")

        return filtered_data

    def get_filtered_stocks(self, force_refresh: bool = False) -> List[str]:
        """
        Get cached filtered stocks or compute them if cache is expired.
        
        Args:
            force_refresh: Force refresh of the cache
            
        Returns:
            List of filtered stock symbols
        """
        # Check if cache is valid
        if (not force_refresh and 
            self._filtered_stocks_cache is not None and 
            self._cache_timestamp is not None):
            
            cache_age = datetime.now() - self._cache_timestamp
            if cache_age.total_seconds() < (self._cache_duration_hours * 3600):
                self._log(f"Using cached filtered stocks ({len(self._filtered_stocks_cache)} stocks)")
                return self._filtered_stocks_cache
        
        # Compute filtered stocks
        self._log("Computing fresh filtered stock list...")
        filtered_stocks = self.apply_comprehensive_filter()
        
        # Update cache
        self._filtered_stocks_cache = filtered_stocks
        self._cache_timestamp = datetime.now()
        
        return filtered_stocks
    
    def get_filter_summary(self) -> Dict[str, any]:
        """
        Get a summary of filtering results.

        Returns:
            Dictionary with filtering statistics
        """
        # Get total stocks
        result = self.db_manager.execute_query("SELECT COUNT(*) FROM tradable_stocks")
        total_stocks = result[1][0][0] if result and result[1] else 0
        
        # Get stocks by series
        series_filtered = self.get_stocks_by_series()
        
        # Get final filtered stocks
        final_filtered = self.get_filtered_stocks()
        
        return {
            'total_stocks': total_stocks,
            'after_series_filter': len(series_filtered),
            'final_filtered': len(final_filtered),
            'be_bz_excluded': total_stocks - len(series_filtered),
            'total_excluded': total_stocks - len(final_filtered),
            'efficiency_gain_percent': round((total_stocks - len(final_filtered)) / total_stocks * 100, 1)
        }


def main():
    """Test the stock filtering system."""
    print("STOCK FILTERING SYSTEM TEST")
    print("=" * 50)
    
    # Initialize filter
    stock_filter = StockFilter(
        min_market_cap_cr=100.0,  # 100 crores
        min_daily_value_l=10.0,   # 10 lakhs
        verbose=True
    )
    
    # Get filter summary
    summary = stock_filter.get_filter_summary()
    
    print("\nFILTERING SUMMARY:")
    print(f"Total stocks in database: {summary['total_stocks']}")
    print(f"After series filter (exclude BE/BZ): {summary['after_series_filter']}")
    print(f"Final filtered stocks: {summary['final_filtered']}")
    print(f"BE/BZ stocks excluded: {summary['be_bz_excluded']}")
    print(f"Total stocks excluded: {summary['total_excluded']}")
    print(f"Efficiency gain: {summary['efficiency_gain_percent']}%")


if __name__ == "__main__":
    main()
