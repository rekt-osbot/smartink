#!/usr/bin/env python3
"""
Quick test script to verify yfinance integration with popular NSE stocks.
"""

import sys
from stock_data_fetcher import StockDataFetcher


def test_popular_stocks():
    """Test fetching data for popular NSE stocks."""
    print("Testing yfinance integration with popular NSE stocks...")
    print("=" * 60)
    
    fetcher = StockDataFetcher(verbose=True)
    
    # Get popular stocks
    popular_stocks = fetcher.get_popular_nse_stocks()
    print(f"Testing with {len(popular_stocks)} popular stocks")
    
    # Test first 5 stocks
    test_stocks = popular_stocks[:5]
    print(f"Testing: {', '.join(test_stocks)}")
    print("-" * 60)
    
    successful = 0
    failed = 0
    
    for symbol in test_stocks:
        print(f"\nTesting {symbol}...")
        data = fetcher.fetch_stock_data(symbol, period="1mo")
        
        if data is not None and not data.empty:
            print(f"✓ {symbol}: {len(data)} records fetched")
            successful += 1
        else:
            print(f"✗ {symbol}: No data")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {successful} successful, {failed} failed")
    print(f"Success rate: {(successful/(successful+failed)*100):.1f}%")
    
    if successful > 0:
        print("✓ yfinance integration is working!")
        return True
    else:
        print("✗ yfinance integration has issues")
        return False


if __name__ == "__main__":
    try:
        success = test_popular_stocks()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
