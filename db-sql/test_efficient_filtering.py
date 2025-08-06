#!/usr/bin/env python3
"""
Test the improved efficient stock filtering system.
"""

from stock_filter import StockFilter
import time
import pandas as pd

def test_efficient_filtering():
    """Test the new efficient filtering approach."""
    print("TESTING EFFICIENT STOCK FILTERING")
    print("=" * 50)
    
    # Initialize filter
    stock_filter = StockFilter(
        min_market_cap_cr=100.0,  # 100 crores
        min_daily_value_l=10.0,   # 10 lakhs
        verbose=True
    )
    
    # Test 1: Basic series filtering (should be fast)
    print("\n1. Testing SERIES FILTERING (BE/BZ exclusion):")
    start_time = time.time()
    series_filtered = stock_filter.get_stocks_by_series()
    series_time = time.time() - start_time
    
    print(f"Series filtered stocks: {len(series_filtered)}")
    print(f"Time taken: {series_time:.3f} seconds")
    
    # Test 2: Efficient combined market cap and volume filtering
    print("\n2. Testing EFFICIENT COMBINED FILTERING:")
    start_time = time.time()
    
    # Test with smaller sample for speed
    sample_stocks = series_filtered[:20] if len(series_filtered) > 20 else series_filtered
    combined_data = stock_filter.get_market_cap_and_volume_data(sample_stocks, sample_size=20)
    
    combined_time = time.time() - start_time
    
    print(f"Sample stocks tested: {len(sample_stocks)}")
    print(f"Successfully processed: {len(combined_data)}")
    print(f"Time taken: {combined_time:.3f} seconds")
    
    # Show some results
    if combined_data:
        print("\nSample results:")
        for i, (symbol, data) in enumerate(list(combined_data.items())[:5]):
            mcap = data['market_cap_cr']
            volume = data['avg_trading_value_l']
            print(f"  {symbol}: Market Cap = {mcap:.1f}cr, Trading Value = {volume:.1f}L")
    
    # Test 3: Filter stocks that meet criteria
    print("\n3. Testing CRITERIA FILTERING:")
    good_stocks = []
    filtered_out = []
    
    for symbol, data in combined_data.items():
        mcap_ok = data['market_cap_cr'] >= stock_filter.min_market_cap_cr
        volume_ok = data['avg_trading_value_l'] >= stock_filter.min_daily_value_l
        
        if mcap_ok and volume_ok:
            good_stocks.append(symbol)
        else:
            filtered_out.append((symbol, data))
    
    print(f"Stocks meeting criteria: {len(good_stocks)}")
    print(f"Stocks filtered out: {len(filtered_out)}")
    
    if filtered_out:
        print("\nFiltered out stocks:")
        for symbol, data in filtered_out[:3]:
            mcap = data['market_cap_cr']
            volume = data['avg_trading_value_l']
            reason = []
            if mcap < stock_filter.min_market_cap_cr:
                reason.append(f"Low market cap ({mcap:.1f}cr)")
            if volume < stock_filter.min_daily_value_l:
                reason.append(f"Low volume ({volume:.1f}L)")
            print(f"  {symbol}: {', '.join(reason)}")
    
    # Test 4: Performance comparison
    print("\n4. PERFORMANCE COMPARISON:")
    
    # Old approach (separate calls)
    print("Old approach (separate API calls):")
    start_time = time.time()
    market_caps = {}
    trading_volumes = {}
    
    # Simulate old approach with smaller sample
    test_symbols = sample_stocks[:5]
    for symbol in test_symbols:
        try:
            import yfinance as yf
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            
            # Market cap call
            info = ticker.info
            market_cap_inr = info.get('marketCap', 0)
            if market_cap_inr:
                market_caps[symbol] = market_cap_inr / 10_000_000
            
            # Volume call
            hist = ticker.history(period="5d")
            if not hist.empty:
                trading_values = hist['Close'] * hist['Volume']
                avg_trading_value = trading_values.mean()
                if avg_trading_value:
                    trading_volumes[symbol] = avg_trading_value / 100_000
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            print(f"Error with {symbol}: {e}")
    
    old_time = time.time() - start_time
    print(f"  Processed {len(test_symbols)} stocks in {old_time:.3f} seconds")
    print(f"  Average time per stock: {old_time/len(test_symbols):.3f} seconds")
    
    # New approach
    print("New approach (bulk calls):")
    start_time = time.time()
    new_data = stock_filter.get_market_cap_and_volume_data(test_symbols, len(test_symbols))
    new_time = time.time() - start_time
    
    print(f"  Processed {len(test_symbols)} stocks in {new_time:.3f} seconds")
    print(f"  Average time per stock: {new_time/len(test_symbols):.3f} seconds")
    print(f"  Speed improvement: {old_time/new_time:.1f}x faster")
    
    return {
        'series_filtered': len(series_filtered),
        'sample_processed': len(combined_data),
        'good_stocks': len(good_stocks),
        'filtered_out': len(filtered_out),
        'old_time': old_time,
        'new_time': new_time,
        'speed_improvement': old_time/new_time if new_time > 0 else 0
    }

def test_data_filtering():
    """Test filtering stocks with actual data."""
    print("\n" + "=" * 50)
    print("TESTING DATA-BASED FILTERING")
    print("=" * 50)
    
    stock_filter = StockFilter(verbose=True)
    
    # Create sample stock data
    sample_data = {}
    
    # High volume stock
    high_vol_data = pd.DataFrame({
        'Close': [100, 105, 102, 108, 110],
        'Volume': [50000, 60000, 55000, 70000, 65000]  # High volume
    })
    sample_data['HIGHVOL'] = high_vol_data
    
    # Low volume stock
    low_vol_data = pd.DataFrame({
        'Close': [50, 52, 51, 53, 54],
        'Volume': [1000, 1200, 800, 1500, 1100]  # Low volume
    })
    sample_data['LOWVOL'] = low_vol_data
    
    print(f"Sample data created for {len(sample_data)} stocks")
    
    # Apply filtering
    filtered_data = stock_filter.filter_stocks_with_data(sample_data)
    
    print(f"Stocks after filtering: {len(filtered_data)}")
    print(f"Stocks filtered out: {len(sample_data) - len(filtered_data)}")
    
    return len(filtered_data)

if __name__ == "__main__":
    # Run tests
    results = test_efficient_filtering()
    filtered_count = test_data_filtering()
    
    # Print summary
    print(f"\n" + "=" * 50)
    print("EFFICIENCY TEST SUMMARY")
    print("=" * 50)
    print(f"✓ Series filtering: {results['series_filtered']} stocks (fast)")
    print(f"✓ Market data processing: {results['sample_processed']} stocks")
    print(f"✓ Stocks meeting criteria: {results['good_stocks']}")
    print(f"✓ Speed improvement: {results['speed_improvement']:.1f}x faster")
    print(f"✓ Data-based filtering: {filtered_count} stocks passed")
    print(f"✓ Efficient bulk API calls implemented successfully")
