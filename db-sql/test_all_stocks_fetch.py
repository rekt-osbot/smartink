#!/usr/bin/env python3
"""
Test script to demonstrate fetching data for ALL NSE stocks vs just popular ones.
"""

from technical_analysis import TechnicalAnalyzer
from stock_data_fetcher import StockDataFetcher


def test_stock_counts():
    """Test and compare stock counts."""
    print("=" * 60)
    print("TESTING STOCK DATA FETCH CAPABILITIES")
    print("=" * 60)
    
    fetcher = StockDataFetcher(verbose=True)
    analyzer = TechnicalAnalyzer(verbose=True)
    
    # Get all stocks from database
    all_stocks = fetcher.get_stocks_from_database(use_popular_only=False)
    popular_stocks = fetcher.get_popular_nse_stocks()
    popular_in_db = fetcher.get_stocks_from_database(use_popular_only=True)
    
    print(f"\n📊 STOCK COUNT COMPARISON:")
    print(f"• Total NSE stocks in database: {len(all_stocks)}")
    print(f"• Popular stocks (hardcoded): {len(popular_stocks)}")
    print(f"• Popular stocks in database: {len(popular_in_db)}")
    
    print(f"\n📋 SAMPLE STOCKS:")
    print(f"• First 10 NSE stocks: {all_stocks[:10]}")
    print(f"• Popular stocks: {popular_stocks[:10]}")
    
    print(f"\n🔧 FETCH OPTIONS:")
    print(f"• OLD way (popular only): Would fetch {len(popular_stocks)} stocks")
    print(f"• NEW way (all NSE): Can fetch all {len(all_stocks)} stocks")
    print(f"• NEW way (with limit): Can fetch any number up to {len(all_stocks)}")
    
    print(f"\n✅ CONCLUSION:")
    print(f"The updated system can now fetch data for ALL {len(all_stocks)} NSE tradable stocks")
    print(f"instead of being limited to just {len(popular_stocks)} popular ones!")
    
    return len(all_stocks), len(popular_stocks)


if __name__ == "__main__":
    try:
        total_nse, total_popular = test_stock_counts()
        print(f"\n🎉 SUCCESS: System can now handle {total_nse} stocks instead of just {total_popular}!")
    except Exception as e:
        print(f"❌ Error: {e}")
