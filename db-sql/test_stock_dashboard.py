#!/usr/bin/env python3
"""
Test script for the stock dashboard functionality.
This script demonstrates the key features without requiring user interaction.
"""

import sys
from datetime import datetime

from technical_analysis import TechnicalAnalyzer
from stock_data_fetcher import StockDataFetcher
from stock_data_manager import StockDataManager
from utils import print_section_header
from config import CONSOLE_WIDTH


def test_stock_dashboard():
    """Test the stock dashboard functionality."""
    print_section_header("STOCK DASHBOARD TEST", CONSOLE_WIDTH)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * CONSOLE_WIDTH)
    
    try:
        # Initialize components
        print("\n1. Initializing components...")
        analyzer = TechnicalAnalyzer(verbose=True)
        fetcher = StockDataFetcher(verbose=True)
        data_manager = StockDataManager(verbose=True)
        
        print("✓ All components initialized successfully")
        
        # Setup database schema
        print("\n2. Setting up database schema...")
        if analyzer.setup_database():
            print("✓ Database schema setup completed")
        else:
            print("✗ Database schema setup failed")
            return False
        
        # Get a few test symbols from the database
        print("\n3. Getting test symbols from database...")
        symbols = fetcher.get_stocks_from_database()
        
        if not symbols:
            print("✗ No symbols found in database")
            print("Please run the main application first to populate the database")
            return False
        
        # Use first 5 symbols for testing
        test_symbols = symbols[:5]
        print(f"✓ Using test symbols: {', '.join(test_symbols)}")
        
        # Fetch sample data
        print("\n4. Fetching sample stock data...")
        stock_data = fetcher.fetch_multiple_stocks(test_symbols, period="1mo")
        
        if not stock_data:
            print("✗ No data fetched")
            return False
        
        print(f"✓ Fetched data for {len(stock_data)} stocks")
        
        # Store data in database
        print("\n5. Storing data in database...")
        total_records = 0
        for symbol, data in stock_data.items():
            if data is not None and not data.empty:
                if data_manager.insert_price_data(data):
                    total_records += len(data)
                
                # Store indicators
                indicators_data = data[['symbol', 'date', 'sma_20']].copy()
                data_manager.insert_indicators_data(indicators_data)
        
        print(f"✓ Stored {total_records} price records")
        
        # Test analysis functions
        print("\n6. Testing analysis functions...")
        
        # Test stocks above SMA
        stocks_above_sma = analyzer.get_stocks_above_sma(20)
        if stocks_above_sma is not None:
            print(f"✓ Found {len(stocks_above_sma)} stocks above 20-day SMA")
        else:
            print("• No stocks above 20-day SMA found")
        
        # Test open=high patterns
        open_high_patterns = analyzer.get_open_high_patterns()
        if open_high_patterns is not None:
            print(f"✓ Found {len(open_high_patterns)} open=high patterns")
        else:
            print("• No open=high patterns found")
        
        # Display summary
        print("\n7. Summary statistics:")
        stats = analyzer.get_summary_statistics()
        for key, value in stats.items():
            print(f"• {key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "=" * CONSOLE_WIDTH)
        print("✓ STOCK DASHBOARD TEST COMPLETED SUCCESSFULLY!")
        print("You can now run the main application and use option 3 to access the dashboard.")
        print("=" * CONSOLE_WIDTH)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for the test."""
    try:
        success = test_stock_dashboard()
        if success:
            print("\nTest completed successfully!")
        else:
            print("\nTest failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
