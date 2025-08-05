#!/usr/bin/env python3
"""
Test script to verify cloud detection and database path handling.
"""

import os
import tempfile
from pathlib import Path

def test_cloud_detection():
    """Test cloud environment detection."""
    print("=" * 60)
    print("TESTING CLOUD ENVIRONMENT DETECTION")
    print("=" * 60)
    
    # Check current environment
    print("Current Environment:")
    print(f"  STREAMLIT_SHARING_MODE: {os.getenv('STREAMLIT_SHARING_MODE', 'Not set')}")
    print(f"  STREAMLIT_CLOUD: {os.getenv('STREAMLIT_CLOUD', 'Not set')}")
    
    # Test cloud detection function
    def is_streamlit_cloud():
        return bool(os.getenv('STREAMLIT_SHARING_MODE') or os.getenv('STREAMLIT_CLOUD'))
    
    is_cloud = is_streamlit_cloud()
    print(f"  Detected as cloud: {is_cloud}")
    
    # Test database path logic
    print(f"\nDatabase Path Logic:")
    if is_cloud:
        db_path = os.path.join(tempfile.gettempdir(), "tradable_stocks.db")
        print(f"  Cloud path: {db_path}")
    else:
        db_path = "tradable_stocks.db"
        print(f"  Local path: {db_path}")
    
    print(f"  Resolved path: {Path(db_path).absolute()}")
    print(f"  Temp directory: {tempfile.gettempdir()}")
    
    # Test config import
    print(f"\nTesting Config Import:")
    try:
        from config import DB_FILE
        print(f"  Config DB_FILE: {DB_FILE}")
        print(f"  Config path exists: {Path(DB_FILE).exists()}")
    except Exception as e:
        print(f"  Config import error: {e}")
    
    # Test database manager
    print(f"\nTesting Database Manager:")
    try:
        from database_manager import DatabaseManager
        db_manager = DatabaseManager(verbose=True)
        print(f"  Database file: {db_manager.db_file}")
        print(f"  File exists: {Path(db_manager.db_file).exists()}")
        
        # Test connection
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"  Tables found: {len(tables)}")
            for table in tables:
                print(f"    - {table[0]}")
                
    except Exception as e:
        print(f"  Database manager error: {e}")
    
    # Recommendations
    print(f"\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if is_cloud:
        print("✅ Running on Streamlit Cloud:")
        print("  • Database will be stored in temp directory")
        print("  • Data will be lost on app restart")
        print("  • Users need to fetch data each session")
        print("  • This is expected behavior")
    else:
        print("✅ Running locally:")
        print("  • Database will be stored in current directory")
        print("  • Data will persist between runs")
        print("  • Normal operation expected")
    
    return True


if __name__ == "__main__":
    try:
        test_cloud_detection()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
