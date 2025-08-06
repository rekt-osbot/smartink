"""
Optimized stock filtering utility that eliminates N+1 query problems.
This version focuses on fast series filtering and post-fetch data filtering.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Tuple
from database_manager import DatabaseManager
from config import DB_FILE


class OptimizedStockFilter:
    """
    High-performance stock filtering system that eliminates API bottlenecks.
    
    Strategy:
    1. Fast series filtering (BE/BZ exclusion) using local DB queries
    2. Post-fetch filtering using already downloaded OHLCV data
    3. No pre-fetch market cap/volume API calls (eliminates N+1 problem)
    """
    
    def __init__(self, 
                 min_daily_value_l: float = 10.0,   # 10 lakhs INR minimum daily trading value
                 verbose: bool = True):
        """
        Initialize the optimized stock filter.
        
        Args:
            min_daily_value_l: Minimum daily trading value in lakhs (default: 10)
            verbose: Whether to print detailed information
        """
        self.min_daily_value_l = min_daily_value_l
        self.verbose = verbose
        self.db_manager = DatabaseManager(verbose=verbose)
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[OptimizedFilter] {message}")
    
    def get_series_filtered_stocks(self, excluded_series: List[str] = None) -> List[str]:
        """
        Get stocks filtered by series (category) - FAST local DB operation.
        
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
    
    def filter_fetched_data_by_volume(self, stock_data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Filter stocks based on trading volume using already fetched OHLCV data.
        This is FAST because it uses data we already have - no additional API calls.
        
        Args:
            stock_data_dict: Dictionary mapping symbols to their OHLCV DataFrames
            
        Returns:
            Filtered dictionary with only stocks meeting volume criteria
        """
        if not stock_data_dict:
            return {}
        
        filtered_data = {}
        volume_filtered_count = 0
        
        self._log(f"Filtering {len(stock_data_dict)} stocks by trading volume...")
        
        for symbol, data in stock_data_dict.items():
            try:
                if data is None or data.empty:
                    continue
                
                # Check trading volume criteria using fetched data
                volume_ok = True
                if 'Volume' in data.columns and 'Close' in data.columns:
                    # Calculate average daily trading value from the fetched data
                    data_clean = data.dropna()
                    if len(data_clean) > 0:
                        trading_values = data_clean['Close'] * data_clean['Volume']
                        avg_trading_value = trading_values.mean()
                        avg_trading_value_l = avg_trading_value / 100_000  # Convert to lakhs
                        
                        if avg_trading_value_l < self.min_daily_value_l:
                            volume_ok = False
                            volume_filtered_count += 1
                
                if volume_ok:
                    filtered_data[symbol] = data
                    
            except Exception as e:
                self._log(f"Error filtering {symbol}: {e}")
                # Include stock if there's an error (conservative approach)
                filtered_data[symbol] = data
        
        self._log(f"Volume filter: {volume_filtered_count} stocks filtered out")
        self._log(f"Remaining stocks: {len(filtered_data)}")
        
        return filtered_data
    
    def get_optimized_stock_list(self) -> List[str]:
        """
        Get optimized stock list using FAST series filtering only.
        No slow API calls - just local database queries.
        
        Returns:
            List of stock symbols optimized for fetching
        """
        self._log("Getting optimized stock list (series filtering only)...")
        
        # Only do fast series filtering - no slow API calls
        filtered_stocks = self.get_series_filtered_stocks()
        
        self._log(f"Optimized stock list: {len(filtered_stocks)} stocks")
        return filtered_stocks
    
    def get_filter_summary(self) -> Dict[str, any]:
        """
        Get a summary of filtering capabilities.
        
        Returns:
            Dictionary with filtering statistics
        """
        # Get total stocks
        result = self.db_manager.execute_query("SELECT COUNT(*) FROM tradable_stocks")
        total_stocks = result[1][0][0] if result and result[1] else 0
        
        # Get stocks by series (fast operation)
        series_filtered = self.get_series_filtered_stocks()
        
        return {
            'total_stocks': total_stocks,
            'series_filtered': len(series_filtered),
            'be_bz_excluded': total_stocks - len(series_filtered),
            'efficiency_gain_percent': round((total_stocks - len(series_filtered)) / total_stocks * 100, 1),
            'filtering_strategy': 'optimized_post_fetch'
        }


class PostFetchFilter:
    """
    Utility class for filtering stocks after data has been fetched.
    This eliminates all pre-fetch API bottlenecks.
    """
    
    def __init__(self, min_market_cap_cr: float = 100.0, min_daily_value_l: float = 10.0):
        """
        Initialize post-fetch filter.
        
        Args:
            min_market_cap_cr: Minimum market cap in crores (for future use)
            min_daily_value_l: Minimum daily trading value in lakhs
        """
        self.min_market_cap_cr = min_market_cap_cr
        self.min_daily_value_l = min_daily_value_l
    
    def filter_by_volume(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Filter stocks by trading volume using fetched data.
        
        Args:
            stock_data: Dictionary of symbol -> DataFrame
            
        Returns:
            Filtered dictionary
        """
        filtered = {}
        
        for symbol, df in stock_data.items():
            if df is None or df.empty:
                continue
                
            try:
                # Calculate average trading value
                if 'Close' in df.columns and 'Volume' in df.columns:
                    df_clean = df.dropna()
                    if len(df_clean) > 0:
                        trading_values = df_clean['Close'] * df_clean['Volume']
                        avg_value_l = trading_values.mean() / 100_000
                        
                        if avg_value_l >= self.min_daily_value_l:
                            filtered[symbol] = df
                else:
                    # Include if we can't calculate (conservative)
                    filtered[symbol] = df
                    
            except Exception:
                # Include if error (conservative)
                filtered[symbol] = df
        
        return filtered
    
    def get_volume_stats(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Get volume statistics for fetched stocks.
        
        Args:
            stock_data: Dictionary of symbol -> DataFrame
            
        Returns:
            Dictionary of symbol -> average daily trading value in lakhs
        """
        stats = {}
        
        for symbol, df in stock_data.items():
            if df is None or df.empty:
                continue
                
            try:
                if 'Close' in df.columns and 'Volume' in df.columns:
                    df_clean = df.dropna()
                    if len(df_clean) > 0:
                        trading_values = df_clean['Close'] * df_clean['Volume']
                        avg_value_l = trading_values.mean() / 100_000
                        stats[symbol] = avg_value_l
                        
            except Exception:
                continue
        
        return stats


def main():
    """Test the optimized filtering system."""
    print("OPTIMIZED STOCK FILTERING TEST")
    print("=" * 50)
    
    # Initialize optimized filter
    opt_filter = OptimizedStockFilter(min_daily_value_l=10.0, verbose=True)
    
    # Test fast series filtering
    import time
    start_time = time.time()
    optimized_stocks = opt_filter.get_optimized_stock_list()
    filter_time = time.time() - start_time
    
    print(f"Optimized filtering completed in {filter_time:.3f} seconds")
    print(f"Stocks ready for fetching: {len(optimized_stocks)}")
    
    # Get summary
    summary = opt_filter.get_filter_summary()
    print(f"\nOptimized Filter Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Test post-fetch filtering with sample data
    print(f"\nTesting post-fetch filtering...")
    post_filter = PostFetchFilter()
    
    # Create sample data
    sample_data = {
        'HIGHVOL': pd.DataFrame({
            'Close': [100, 105, 102],
            'Volume': [50000, 60000, 55000]  # High volume
        }),
        'LOWVOL': pd.DataFrame({
            'Close': [50, 52, 51],
            'Volume': [1000, 1200, 800]  # Low volume
        })
    }
    
    filtered_sample = post_filter.filter_by_volume(sample_data)
    volume_stats = post_filter.get_volume_stats(sample_data)
    
    print(f"Sample data: {len(sample_data)} stocks")
    print(f"After volume filter: {len(filtered_sample)} stocks")
    print(f"Volume stats: {volume_stats}")


if __name__ == "__main__":
    main()
