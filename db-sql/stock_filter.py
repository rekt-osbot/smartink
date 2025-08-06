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
    
    def get_market_cap_data(self, symbols: List[str], sample_size: int = 50) -> Dict[str, float]:
        """
        Get market cap data for a sample of stocks to establish filtering criteria.
        
        Args:
            symbols: List of stock symbols
            sample_size: Number of stocks to sample for market cap analysis
            
        Returns:
            Dictionary mapping symbols to market cap in crores
        """
        if not symbols:
            return {}
        
        # Sample stocks to avoid hitting API limits
        sample_symbols = symbols[:sample_size] if len(symbols) > sample_size else symbols
        market_caps = {}
        
        self._log(f"Fetching market cap data for {len(sample_symbols)} stocks...")
        
        for i, symbol in enumerate(sample_symbols):
            try:
                # Convert NSE symbol to yfinance format
                yf_symbol = f"{symbol}.NS"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                # Get market cap in INR
                market_cap_inr = info.get('marketCap', 0)
                if market_cap_inr and market_cap_inr > 0:
                    # Convert to crores (1 crore = 10 million)
                    market_cap_cr = market_cap_inr / 10_000_000
                    market_caps[symbol] = market_cap_cr
                
                # Rate limiting
                if i < len(sample_symbols) - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                self._log(f"Error fetching market cap for {symbol}: {e}")
                continue
        
        self._log(f"Successfully fetched market cap for {len(market_caps)} stocks")
        return market_caps
    
    def get_trading_volume_data(self, symbols: List[str], sample_size: int = 50) -> Dict[str, float]:
        """
        Get recent trading volume data to filter low-volume stocks.
        
        Args:
            symbols: List of stock symbols
            sample_size: Number of stocks to sample for volume analysis
            
        Returns:
            Dictionary mapping symbols to average daily trading value in lakhs
        """
        if not symbols:
            return {}
        
        # Sample stocks to avoid hitting API limits
        sample_symbols = symbols[:sample_size] if len(symbols) > sample_size else symbols
        trading_values = {}
        
        self._log(f"Fetching trading volume data for {len(sample_symbols)} stocks...")
        
        for i, symbol in enumerate(sample_symbols):
            try:
                # Convert NSE symbol to yfinance format
                yf_symbol = f"{symbol}.NS"
                ticker = yf.Ticker(yf_symbol)
                
                # Get last 5 days of data
                hist = ticker.history(period="5d")
                if not hist.empty and len(hist) > 0:
                    # Calculate average daily trading value (price * volume)
                    hist['trading_value'] = hist['Close'] * hist['Volume']
                    avg_trading_value = hist['trading_value'].mean()
                    
                    if avg_trading_value and avg_trading_value > 0:
                        # Convert to lakhs (1 lakh = 100,000)
                        avg_trading_value_l = avg_trading_value / 100_000
                        trading_values[symbol] = avg_trading_value_l
                
                # Rate limiting
                if i < len(sample_symbols) - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                self._log(f"Error fetching trading volume for {symbol}: {e}")
                continue
        
        self._log(f"Successfully fetched trading volume for {len(trading_values)} stocks")
        return trading_values
    
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
        
        # Step 2: Apply market cap filter if requested
        if use_market_cap:
            market_caps = self.get_market_cap_data(stocks_after_series, sample_size)
            if market_caps:
                # Filter stocks with sufficient market cap
                stocks_with_good_mcap = [
                    symbol for symbol, mcap in market_caps.items() 
                    if mcap >= self.min_market_cap_cr
                ]
                self._log(f"After market cap filter (>={self.min_market_cap_cr}cr): {len(stocks_with_good_mcap)} stocks")
                
                # For stocks without market cap data, include them (conservative approach)
                stocks_without_mcap = [s for s in stocks_after_series if s not in market_caps]
                filtered_stocks = stocks_with_good_mcap + stocks_without_mcap
            else:
                filtered_stocks = stocks_after_series
        else:
            filtered_stocks = stocks_after_series
        
        # Step 3: Apply trading volume filter if requested
        if use_trading_volume:
            trading_volumes = self.get_trading_volume_data(filtered_stocks, sample_size)
            if trading_volumes:
                # Filter stocks with sufficient trading volume
                stocks_with_good_volume = [
                    symbol for symbol, volume in trading_volumes.items() 
                    if volume >= self.min_daily_value_l
                ]
                self._log(f"After trading volume filter (>={self.min_daily_value_l}L): {len(stocks_with_good_volume)} stocks")
                
                # For stocks without volume data, include them (conservative approach)
                stocks_without_volume = [s for s in filtered_stocks if s not in trading_volumes]
                final_filtered_stocks = stocks_with_good_volume + stocks_without_volume
            else:
                final_filtered_stocks = filtered_stocks
        else:
            final_filtered_stocks = filtered_stocks
        
        # Sort the final list
        final_filtered_stocks.sort()
        
        self._log(f"Final filtered stock count: {len(final_filtered_stocks)}")
        self._log(f"Reduction: {len(stocks_after_series) - len(final_filtered_stocks)} stocks filtered out")
        
        return final_filtered_stocks
    
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
    
    def get_filter_summary(self) -> Dict[str, int]:
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
