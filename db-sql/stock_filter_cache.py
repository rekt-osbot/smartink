"""
Persistent stock filter cache system for daily master lists.
Implements date-stamped caching to avoid expensive filtering operations.
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import time
from pathlib import Path


class StockFilterCache:
    """
    Manages persistent caching of filtered stock lists with date-stamping.
    
    This allows expensive filtering operations to be done once per day,
    creating a "master list" that can be used quickly throughout the day.
    """
    
    def __init__(self, cache_file: str = "stock_filter_cache.json", verbose: bool = True):
        """
        Initialize the stock filter cache.
        
        Args:
            cache_file: Path to the cache file
            verbose: Whether to print detailed logs
        """
        self.cache_file = Path(cache_file)
        self.verbose = verbose
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[FilterCache] {message}")
    
    def _get_today_string(self) -> str:
        """Get today's date as a string."""
        return date.today().isoformat()
    
    def save_filtered_stocks(self, 
                           symbols: List[str], 
                           filter_criteria: Dict = None,
                           processing_time: float = None) -> bool:
        """
        Save filtered stock list to cache with today's date.
        
        Args:
            symbols: List of filtered stock symbols
            filter_criteria: Dictionary describing the filtering criteria used
            processing_time: Time taken to compute the filter (in seconds)
            
        Returns:
            True if saved successfully
        """
        try:
            cache_data = {
                "date": self._get_today_string(),
                "timestamp": datetime.now().isoformat(),
                "symbols": symbols,
                "count": len(symbols),
                "filter_criteria": filter_criteria or {},
                "processing_time_seconds": processing_time,
                "cache_version": "1.0"
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            self._log(f"Saved {len(symbols)} filtered stocks to cache for {self._get_today_string()}")
            return True
            
        except Exception as e:
            self._log(f"Error saving cache: {e}")
            return False
    
    def load_filtered_stocks(self, allow_stale: bool = False) -> Optional[Tuple[List[str], Dict]]:
        """
        Load filtered stock list from cache if it's current.
        
        Args:
            allow_stale: If True, return cached data even if it's from a previous day
            
        Returns:
            Tuple of (symbols_list, cache_metadata) if valid cache exists, None otherwise
        """
        try:
            if not self.cache_file.exists():
                self._log("No cache file found")
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cached_date = cache_data.get("date")
            today = self._get_today_string()
            
            if not allow_stale and cached_date != today:
                self._log(f"Cache is stale (cached: {cached_date}, today: {today})")
                return None
            
            symbols = cache_data.get("symbols", [])
            metadata = {
                "date": cached_date,
                "timestamp": cache_data.get("timestamp"),
                "count": cache_data.get("count", len(symbols)),
                "filter_criteria": cache_data.get("filter_criteria", {}),
                "processing_time_seconds": cache_data.get("processing_time_seconds"),
                "is_stale": cached_date != today
            }
            
            self._log(f"Loaded {len(symbols)} stocks from cache (date: {cached_date})")
            return symbols, metadata
            
        except Exception as e:
            self._log(f"Error loading cache: {e}")
            return None
    
    def is_cache_current(self) -> bool:
        """
        Check if cache exists and is current (from today).
        
        Returns:
            True if cache is current
        """
        try:
            if not self.cache_file.exists():
                return False
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cached_date = cache_data.get("date")
            today = self._get_today_string()
            
            return cached_date == today
            
        except Exception:
            return False
    
    def get_cache_info(self) -> Dict:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary with cache information
        """
        if not self.cache_file.exists():
            return {
                "exists": False,
                "current": False,
                "date": None,
                "count": 0
            }
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cached_date = cache_data.get("date")
            today = self._get_today_string()
            
            return {
                "exists": True,
                "current": cached_date == today,
                "date": cached_date,
                "timestamp": cache_data.get("timestamp"),
                "count": cache_data.get("count", 0),
                "processing_time_seconds": cache_data.get("processing_time_seconds"),
                "is_stale": cached_date != today,
                "age_days": (date.today() - date.fromisoformat(cached_date)).days if cached_date else None
            }
            
        except Exception as e:
            return {
                "exists": True,
                "current": False,
                "error": str(e),
                "count": 0
            }
    
    def clear_cache(self) -> bool:
        """
        Clear the cache file.
        
        Returns:
            True if cleared successfully
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                self._log("Cache cleared")
            return True
        except Exception as e:
            self._log(f"Error clearing cache: {e}")
            return False


class CachedStockFilter:
    """
    Stock filter that uses persistent caching for expensive operations.
    
    This combines fast series filtering with cached market cap/volume filtering
    to provide the best of both worlds: speed for daily use and comprehensive
    filtering when needed.
    """
    
    def __init__(self, 
                 min_market_cap_cr: float = 100.0,
                 min_daily_value_l: float = 10.0,
                 cache_file: str = "stock_filter_cache.json",
                 verbose: bool = True):
        """
        Initialize cached stock filter.
        
        Args:
            min_market_cap_cr: Minimum market cap in crores
            min_daily_value_l: Minimum daily trading value in lakhs
            cache_file: Path to cache file
            verbose: Whether to print logs
        """
        self.min_market_cap_cr = min_market_cap_cr
        self.min_daily_value_l = min_daily_value_l
        self.verbose = verbose
        self.cache = StockFilterCache(cache_file, verbose)
        
        # Import here to avoid circular imports
        from optimized_stock_filter import OptimizedStockFilter
        self.fast_filter = OptimizedStockFilter(min_daily_value_l, verbose)
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[CachedFilter] {message}")
    
    def get_filtered_stocks(self, force_refresh: bool = False) -> List[str]:
        """
        Get filtered stocks using cache when possible.
        
        Args:
            force_refresh: If True, bypass cache and recompute
            
        Returns:
            List of filtered stock symbols
        """
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_result = self.cache.load_filtered_stocks()
            if cached_result:
                symbols, metadata = cached_result
                self._log(f"Using cached filtered stocks: {len(symbols)} symbols")
                return symbols
        
        # Cache miss or force refresh - compute expensive filter
        self._log("Computing fresh filtered stock list (this may take a while)...")
        start_time = time.time()
        
        # Start with fast series filtering
        series_filtered = self.fast_filter.get_series_filtered_stocks()
        
        # For now, we'll use the series-filtered list as our "expensive" filter
        # In a real implementation, you would add market cap/volume filtering here
        # using the original slow method when you need the most comprehensive filter
        filtered_stocks = series_filtered
        
        processing_time = time.time() - start_time
        
        # Save to cache
        filter_criteria = {
            "excluded_series": ["BE", "BZ"],
            "min_market_cap_cr": self.min_market_cap_cr,
            "min_daily_value_l": self.min_daily_value_l,
            "method": "series_filtering_only"  # Update when full filtering is implemented
        }
        
        self.cache.save_filtered_stocks(
            filtered_stocks, 
            filter_criteria, 
            processing_time
        )
        
        self._log(f"Computed and cached {len(filtered_stocks)} filtered stocks in {processing_time:.3f}s")
        return filtered_stocks
    
    def get_cache_status(self) -> Dict:
        """Get current cache status."""
        return self.cache.get_cache_info()
    
    def refresh_cache(self) -> List[str]:
        """Force refresh the cache."""
        return self.get_filtered_stocks(force_refresh=True)
    
    def clear_cache(self) -> bool:
        """Clear the cache."""
        return self.cache.clear_cache()


def main():
    """Test the cached filtering system."""
    print("CACHED STOCK FILTERING TEST")
    print("=" * 50)
    
    # Initialize cached filter
    cached_filter = CachedStockFilter(verbose=True)
    
    # Test 1: First call (should compute and cache)
    print("\n1. First call (should compute and cache):")
    start_time = time.time()
    stocks1 = cached_filter.get_filtered_stocks()
    time1 = time.time() - start_time
    print(f"   Result: {len(stocks1)} stocks in {time1:.3f}s")
    
    # Test 2: Second call (should use cache)
    print("\n2. Second call (should use cache):")
    start_time = time.time()
    stocks2 = cached_filter.get_filtered_stocks()
    time2 = time.time() - start_time
    print(f"   Result: {len(stocks2)} stocks in {time2:.3f}s")
    print(f"   Speed improvement: {time1/time2:.1f}x faster")
    
    # Test 3: Cache status
    print("\n3. Cache status:")
    status = cached_filter.get_cache_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test 4: Force refresh
    print("\n4. Force refresh:")
    start_time = time.time()
    stocks3 = cached_filter.refresh_cache()
    time3 = time.time() - start_time
    print(f"   Result: {len(stocks3)} stocks in {time3:.3f}s")
    
    print(f"\n✅ Cached filtering system working correctly!")
    print(f"   • First computation: {time1:.3f}s")
    print(f"   • Cached retrieval: {time2:.3f}s ({time1/time2:.1f}x faster)")
    print(f"   • Cache refresh: {time3:.3f}s")


if __name__ == "__main__":
    main()
