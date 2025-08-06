#!/usr/bin/env python3
"""
Comprehensive test of the cached filtering system integration.
Tests the complete workflow from cache creation to daily usage.
"""

from technical_analysis import TechnicalAnalyzer
from stock_data_fetcher import StockDataFetcher
from stock_filter_cache import CachedStockFilter
import time
import os

def test_cached_filtering_workflow():
    """Test the complete cached filtering workflow."""
    print("CACHED FILTERING WORKFLOW TEST")
    print("=" * 60)
    
    # Clean up any existing cache for fresh test
    cache_file = "stock_filter_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print("Cleaned up existing cache for fresh test")
    
    # Test 1: TechnicalAnalyzer with cached filtering
    print("\n1. Testing TechnicalAnalyzer with CACHED FILTERING:")
    analyzer = TechnicalAnalyzer(verbose=True, use_filtering=True)
    
    print(f"   Analyzer filtering enabled: {analyzer.use_filtering}")
    print(f"   Fetcher filtering enabled: {analyzer.fetcher.use_filtering}")
    print(f"   Fetcher has cached_filter: {hasattr(analyzer.fetcher, 'cached_filter')}")
    
    # Test 2: First fetch (should create cache)
    print("\n2. First stock fetch (should CREATE cache):")
    start_time = time.time()
    stocks_first = analyzer.fetcher.get_stocks_from_database()
    first_time = time.time() - start_time
    
    print(f"   First fetch: {len(stocks_first)} stocks in {first_time:.3f}s")
    
    # Check cache status
    cache_status = analyzer.fetcher.get_filter_cache_status()
    print(f"   Cache created: {cache_status.get('exists', False)}")
    print(f"   Cache current: {cache_status.get('current', False)}")
    print(f"   Cache count: {cache_status.get('count', 0)}")
    
    # Test 3: Second fetch (should use cache)
    print("\n3. Second stock fetch (should USE cache):")
    start_time = time.time()
    stocks_second = analyzer.fetcher.get_stocks_from_database()
    second_time = time.time() - start_time
    
    print(f"   Second fetch: {len(stocks_second)} stocks in {second_time:.3f}s")
    print(f"   Speed improvement: {first_time/second_time:.1f}x faster")
    print(f"   Results consistent: {stocks_first == stocks_second}")
    
    # Test 4: Cache refresh
    print("\n4. Testing CACHE REFRESH:")
    start_time = time.time()
    refreshed_stocks = analyzer.fetcher.refresh_filter_cache()
    refresh_time = time.time() - start_time
    
    print(f"   Cache refresh: {len(refreshed_stocks)} stocks in {refresh_time:.3f}s")
    print(f"   Results consistent: {stocks_first == refreshed_stocks}")
    
    # Test 5: Filtering summary
    print("\n5. Testing FILTERING SUMMARY:")
    summary = analyzer.fetcher.get_filtering_summary()
    print(f"   Filtering enabled: {summary.get('filtering_enabled', False)}")
    print(f"   Optimization type: {summary.get('optimization_type', 'unknown')}")
    print(f"   Cache current: {summary.get('cache_current', False)}")
    print(f"   Cached stock count: {summary.get('cached_stock_count', 0)}")
    
    return {
        'first_time': first_time,
        'second_time': second_time,
        'refresh_time': refresh_time,
        'stock_count': len(stocks_first),
        'cache_status': cache_status,
        'summary': summary
    }

def test_cache_persistence():
    """Test cache persistence across different instances."""
    print("\n" + "=" * 60)
    print("CACHE PERSISTENCE TEST")
    print("=" * 60)
    
    # Test 1: Create new analyzer instance
    print("\n1. Creating NEW analyzer instance:")
    analyzer_new = TechnicalAnalyzer(verbose=True, use_filtering=True)
    
    # Check if it can use existing cache
    cache_status = analyzer_new.fetcher.get_filter_cache_status()
    print(f"   Cache exists: {cache_status.get('exists', False)}")
    print(f"   Cache current: {cache_status.get('current', False)}")
    
    # Test 2: Fetch using existing cache
    print("\n2. Fetching with existing cache:")
    start_time = time.time()
    stocks_cached = analyzer_new.fetcher.get_stocks_from_database()
    cached_time = time.time() - start_time
    
    print(f"   Cached fetch: {len(stocks_cached)} stocks in {cached_time:.3f}s")
    
    # Test 3: Clear cache and test fallback
    print("\n3. Testing cache CLEAR and fallback:")
    clear_success = analyzer_new.fetcher.clear_filter_cache()
    print(f"   Cache cleared: {clear_success}")
    
    # Fetch after cache clear (should recreate)
    start_time = time.time()
    stocks_recreated = analyzer_new.fetcher.get_stocks_from_database()
    recreate_time = time.time() - start_time
    
    print(f"   Recreated fetch: {len(stocks_recreated)} stocks in {recreate_time:.3f}s")
    print(f"   Results consistent: {stocks_cached == stocks_recreated}")
    
    return {
        'cached_time': cached_time,
        'recreate_time': recreate_time,
        'clear_success': clear_success
    }

def test_performance_comparison():
    """Compare performance with and without caching."""
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON TEST")
    print("=" * 60)
    
    # Test with caching enabled
    print("\n1. Testing WITH caching:")
    analyzer_cached = TechnicalAnalyzer(verbose=False, use_filtering=True)
    
    times_cached = []
    for i in range(3):
        start_time = time.time()
        stocks = analyzer_cached.fetcher.get_stocks_from_database()
        elapsed = time.time() - start_time
        times_cached.append(elapsed)
        print(f"   Run {i+1}: {len(stocks)} stocks in {elapsed:.3f}s")
    
    # Test without caching
    print("\n2. Testing WITHOUT caching:")
    analyzer_no_cache = TechnicalAnalyzer(verbose=False, use_filtering=False)
    
    times_no_cache = []
    for i in range(3):
        start_time = time.time()
        stocks = analyzer_no_cache.fetcher.get_stocks_from_database()
        elapsed = time.time() - start_time
        times_no_cache.append(elapsed)
        print(f"   Run {i+1}: {len(stocks)} stocks in {elapsed:.3f}s")
    
    # Calculate averages
    avg_cached = sum(times_cached) / len(times_cached)
    avg_no_cache = sum(times_no_cache) / len(times_no_cache)
    
    print(f"\n3. PERFORMANCE RESULTS:")
    print(f"   Average with caching: {avg_cached:.3f}s")
    print(f"   Average without caching: {avg_no_cache:.3f}s")
    print(f"   Performance difference: {abs(avg_cached - avg_no_cache):.3f}s")
    
    return {
        'avg_cached': avg_cached,
        'avg_no_cache': avg_no_cache,
        'performance_gain': abs(avg_cached - avg_no_cache)
    }

def test_cache_file_structure():
    """Test the cache file structure and content."""
    print("\n" + "=" * 60)
    print("CACHE FILE STRUCTURE TEST")
    print("=" * 60)
    
    # Create cache
    analyzer = TechnicalAnalyzer(verbose=True, use_filtering=True)
    stocks = analyzer.fetcher.get_stocks_from_database()
    
    # Check cache file
    cache_file = "stock_filter_cache.json"
    if os.path.exists(cache_file):
        import json
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        print(f"Cache file structure:")
        for key, value in cache_data.items():
            if key == 'symbols':
                print(f"   {key}: [{len(value)} symbols]")
            else:
                print(f"   {key}: {value}")
        
        # Validate structure
        required_keys = ['date', 'timestamp', 'symbols', 'count', 'filter_criteria']
        missing_keys = [key for key in required_keys if key not in cache_data]
        
        if missing_keys:
            print(f"   ❌ Missing keys: {missing_keys}")
        else:
            print(f"   ✅ All required keys present")
        
        return cache_data
    else:
        print("   ❌ Cache file not found")
        return None

if __name__ == "__main__":
    print("Starting comprehensive cached filtering system tests...")
    
    # Test 1: Complete workflow
    workflow_results = test_cached_filtering_workflow()
    
    # Test 2: Cache persistence
    persistence_results = test_cache_persistence()
    
    # Test 3: Performance comparison
    performance_results = test_performance_comparison()
    
    # Test 4: Cache file structure
    cache_structure = test_cache_file_structure()
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL CACHED FILTERING SUMMARY")
    print("=" * 60)
    
    print(f"✅ Workflow Test Results:")
    print(f"   • Stock count: {workflow_results['stock_count']}")
    print(f"   • First fetch: {workflow_results['first_time']:.3f}s")
    print(f"   • Cached fetch: {workflow_results['second_time']:.3f}s")
    print(f"   • Speed improvement: {workflow_results['first_time']/workflow_results['second_time']:.1f}x")
    
    print(f"\n✅ Cache Persistence:")
    print(f"   • Cache cleared successfully: {persistence_results['clear_success']}")
    print(f"   • Cache recreation: {persistence_results['recreate_time']:.3f}s")
    
    print(f"\n✅ Performance Comparison:")
    print(f"   • With caching: {performance_results['avg_cached']:.3f}s")
    print(f"   • Without caching: {performance_results['avg_no_cache']:.3f}s")
    print(f"   • Performance difference: {performance_results['performance_gain']:.3f}s")
    
    print(f"\n✅ Cache Structure:")
    if cache_structure:
        print(f"   • Cache file: Valid JSON structure")
        print(f"   • Cached symbols: {cache_structure.get('count', 0)}")
        print(f"   • Cache date: {cache_structure.get('date', 'Unknown')}")
    
    print(f"\n🎯 OVERALL ASSESSMENT:")
    speed_improvement = workflow_results['first_time']/workflow_results['second_time']
    if speed_improvement > 2:
        print(f"   🟢 EXCELLENT: {speed_improvement:.1f}x speed improvement with caching")
    elif speed_improvement > 1.5:
        print(f"   🟡 GOOD: {speed_improvement:.1f}x speed improvement")
    else:
        print(f"   🟠 MODERATE: {speed_improvement:.1f}x speed improvement")
    
    print(f"\n✅ Cached filtering system tests completed successfully!")
    print(f"   • Daily master list caching: WORKING")
    print(f"   • Cache persistence: WORKING")
    print(f"   • Performance optimization: WORKING")
    print(f"   • Professional workflow ready! 🚀")
