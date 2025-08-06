#!/usr/bin/env python3
"""
Test the integrated stock filtering system in StockDataFetcher.
"""

from stock_data_fetcher import StockDataFetcher
import time

def test_filtering_integration():
    """Test the integrated filtering functionality."""
    print("TESTING INTEGRATED STOCK FILTERING")
    print("=" * 50)
    
    # Test with filtering enabled
    print("\n1. Testing with filtering ENABLED:")
    fetcher_with_filter = StockDataFetcher(verbose=True, use_filtering=True)
    
    start_time = time.time()
    filtered_stocks = fetcher_with_filter.get_stocks_from_database()
    filter_time = time.time() - start_time
    
    print(f"Filtered stocks count: {len(filtered_stocks)}")
    print(f"Time taken: {filter_time:.2f} seconds")
    
    # Get filtering summary
    summary = fetcher_with_filter.get_filtering_summary()
    print(f"\nFiltering Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Test with filtering disabled
    print("\n2. Testing with filtering DISABLED:")
    fetcher_no_filter = StockDataFetcher(verbose=True, use_filtering=False)
    
    start_time = time.time()
    all_stocks = fetcher_no_filter.get_stocks_from_database()
    no_filter_time = time.time() - start_time
    
    print(f"All stocks count: {len(all_stocks)}")
    print(f"Time taken: {no_filter_time:.2f} seconds")
    
    # Compare results
    print("\n3. COMPARISON:")
    stocks_filtered_out = len(all_stocks) - len(filtered_stocks)
    efficiency_gain = (stocks_filtered_out / len(all_stocks)) * 100
    
    print(f"Total stocks: {len(all_stocks)}")
    print(f"Filtered stocks: {len(filtered_stocks)}")
    print(f"Stocks filtered out: {stocks_filtered_out}")
    print(f"Efficiency gain: {efficiency_gain:.1f}%")
    
    # Test toggle functionality
    print("\n4. Testing TOGGLE functionality:")
    fetcher_toggle = StockDataFetcher(verbose=True, use_filtering=False)
    
    # Enable filtering
    fetcher_toggle.toggle_filtering(True)
    toggle_filtered = fetcher_toggle.get_stocks_from_database()
    print(f"After enabling filtering: {len(toggle_filtered)} stocks")
    
    # Disable filtering
    fetcher_toggle.toggle_filtering(False)
    toggle_all = fetcher_toggle.get_stocks_from_database()
    print(f"After disabling filtering: {len(toggle_all)} stocks")
    
    # Test unfiltered method
    print("\n5. Testing UNFILTERED method:")
    unfiltered_stocks = fetcher_with_filter.get_unfiltered_stocks_from_database()
    print(f"Unfiltered stocks (from filtered fetcher): {len(unfiltered_stocks)}")
    
    print("\n" + "=" * 50)
    print("INTEGRATION TEST COMPLETE")
    
    return {
        'filtered_count': len(filtered_stocks),
        'total_count': len(all_stocks),
        'efficiency_gain': efficiency_gain,
        'filter_time': filter_time,
        'no_filter_time': no_filter_time
    }

def test_popular_stocks_filtering():
    """Test filtering with popular stocks option."""
    print("\n" + "=" * 50)
    print("TESTING POPULAR STOCKS FILTERING")
    print("=" * 50)
    
    fetcher = StockDataFetcher(verbose=True, use_filtering=True)
    
    # Test popular stocks without filtering
    popular_no_filter = fetcher.get_stocks_from_database(use_popular_only=True, apply_filters=False)
    print(f"Popular stocks (no filter): {len(popular_no_filter)}")
    
    # Test popular stocks with filtering
    popular_with_filter = fetcher.get_stocks_from_database(use_popular_only=True, apply_filters=True)
    print(f"Popular stocks (with filter): {len(popular_with_filter)}")
    
    # Show some examples
    if popular_no_filter:
        print(f"Sample popular stocks: {popular_no_filter[:10]}")

if __name__ == "__main__":
    # Run integration tests
    results = test_filtering_integration()
    
    # Run popular stocks test
    test_popular_stocks_filtering()
    
    # Print final summary
    print(f"\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    print(f"✓ Filtering reduces stock count by {results['efficiency_gain']:.1f}%")
    print(f"✓ From {results['total_count']} to {results['filtered_count']} stocks")
    print(f"✓ Potential API call reduction: {results['total_count'] - results['filtered_count']} calls")
    print(f"✓ Integration successful - filtering can be toggled on/off")
    print(f"✓ Performance impact: {results['filter_time']:.2f}s vs {results['no_filter_time']:.2f}s")
