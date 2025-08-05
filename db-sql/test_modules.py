#!/usr/bin/env python3
"""
Test script to verify all modules import and work correctly.
"""

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    try:
        from utils import normalize_column_name, clear_screen, print_section_header
        print("✓ utils module imported successfully")
    except Exception as e:
        print(f"✗ utils module import failed: {e}")
        return False
    
    try:
        from config import DB_FILE, TABLE_NAME, PRIMARY_CSV_URL
        print("✓ config module imported successfully")
    except Exception as e:
        print(f"✗ config module import failed: {e}")
        return False
    
    try:
        from data_processor import DataProcessor
        print("✓ data_processor module imported successfully")
    except Exception as e:
        print(f"✗ data_processor module import failed: {e}")
        return False
    
    try:
        from database_manager import DatabaseManager
        print("✓ database_manager module imported successfully")
    except Exception as e:
        print(f"✗ database_manager module import failed: {e}")
        return False
    
    try:
        from main import NSEStocksApp
        print("✓ main module imported successfully")
    except Exception as e:
        print(f"✗ main module import failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality of key modules."""
    print("\nTesting basic functionality...")
    
    # Test utils
    from utils import normalize_column_name
    test_name = normalize_column_name("Company Name & Details")
    expected = "company_name_details"
    if test_name == expected:
        print("✓ normalize_column_name works correctly")
    else:
        print(f"✗ normalize_column_name failed: got '{test_name}', expected '{expected}'")
        return False
    
    # Test data processor initialization
    try:
        from data_processor import DataProcessor
        processor = DataProcessor(verbose=False)
        print("✓ DataProcessor initializes correctly")
    except Exception as e:
        print(f"✗ DataProcessor initialization failed: {e}")
        return False
    
    # Test database manager initialization
    try:
        from database_manager import DatabaseManager
        db_manager = DatabaseManager(verbose=False)
        print("✓ DatabaseManager initializes correctly")
    except Exception as e:
        print(f"✗ DatabaseManager initialization failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 50)
    print("  NSE Stocks Application Module Tests")
    print("=" * 50)
    
    if not test_imports():
        print("\n✗ Import tests failed")
        return False
    
    if not test_basic_functionality():
        print("\n✗ Functionality tests failed")
        return False
    
    print("\n" + "=" * 50)
    print("✓ All tests passed! The refactored application is ready.")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
