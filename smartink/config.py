"""
Configuration settings for the NSE stocks database application.
All configurable parameters should be defined here to maintain consistency across modules.
"""

from pathlib import Path

# Database configuration
import os
import tempfile

# Use temporary directory for cloud deployments
if os.getenv('STREAMLIT_SHARING_MODE') or os.getenv('STREAMLIT_CLOUD'):
    # Running on Streamlit Cloud - use temp directory
    DB_FILE = os.path.join(tempfile.gettempdir(), "tradable_stocks.db")
else:
    # Running locally - use current directory
    DB_FILE = "tradable_stocks.db"

TABLE_NAME = "tradable_stocks"

# Data source URLs
# Primary URL for NSE equity list (more comprehensive data)
PRIMARY_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
# Alternative URL for daily bhav data (simpler structure)
BHAV_CSV_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full.csv"

# Removed LOCAL_CSV_FILES - application now uses URL-based data sources only

# HTTP request configuration
REQUEST_TIMEOUT = 30
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Application settings
APP_TITLE = "NSE Tradable Stocks Database Interface"
CONSOLE_WIDTH = 60

# Date format for database storage
DATE_FORMAT = "%Y-%m-%d"

# Pandas to SQLite type mapping
PANDAS_TO_SQLITE_TYPES = {
    'int64': 'INTEGER',
    'int32': 'INTEGER',
    'int16': 'INTEGER',
    'int8': 'INTEGER',
    'float64': 'REAL',
    'float32': 'REAL',
    'object': 'TEXT',
    'bool': 'INTEGER',
    'datetime64[ns]': 'DATE',
    'category': 'TEXT'
}
