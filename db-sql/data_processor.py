"""
Unified data processing module for NSE stocks data.
This module consolidates all data loading, cleaning, and processing logic.
"""

import pandas as pd
import requests
import io
from pathlib import Path
from typing import Optional, List, Tuple

from utils import normalize_column_name, ensure_file_exists, print_step
from config import (
    PRIMARY_CSV_URL, BHAV_CSV_URL,
    REQUEST_TIMEOUT, REQUEST_HEADERS, DATE_FORMAT
)


class DataProcessor:
    """Handles all data loading, cleaning, and processing operations."""
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the data processor.
        
        Args:
            verbose (bool): Whether to print detailed processing information
        """
        self.verbose = verbose
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def load_csv_from_url(self, url: str) -> Optional[pd.DataFrame]:
        """
        Download and load CSV data from a URL.
        
        Args:
            url (str): The URL to download from
            
        Returns:
            Optional[pd.DataFrame]: The loaded DataFrame or None if failed
        """
        try:
            self._log(f"Fetching data from {url}...")
            response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS)
            
            if response.status_code == 200:
                df = pd.read_csv(io.BytesIO(response.content))
                self._log(f"Successfully downloaded data: {df.shape[0]} rows, {df.shape[1]} columns")
                return df
            else:
                self._log(f"Failed to download: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self._log(f"Error downloading from {url}: {e}")
            return None
    
    def load_csv_from_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Load CSV data from a local file.
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            Optional[pd.DataFrame]: The loaded DataFrame or None if failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
                
            self._log(f"Loading CSV file: {file_path}")
            df = pd.read_csv(file_path)
            self._log(f"Successfully loaded: {df.shape[0]} rows, {df.shape[1]} columns")
            return df
            
        except Exception as e:
            self._log(f"Error loading {file_path}: {e}")
            return None
    
    def load_data_with_fallback(self) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Load data with URL-based fallback strategy.

        Returns:
            Tuple[Optional[pd.DataFrame], str]: DataFrame and source description
        """
        # Try primary URL
        df = self.load_csv_from_url(PRIMARY_CSV_URL)
        if df is not None:
            return df, f"URL: {PRIMARY_CSV_URL}"

        # Try alternative URL
        df = self.load_csv_from_url(BHAV_CSV_URL)
        if df is not None:
            return df, f"URL: {BHAV_CSV_URL}"

        return None, "No data source available"
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize a DataFrame.
        
        Args:
            df (pd.DataFrame): The DataFrame to clean
            
        Returns:
            pd.DataFrame: The cleaned DataFrame
        """
        # Create a copy to avoid modifying the original
        cleaned_df = df.copy()
        
        # Store original columns for comparison
        original_columns = cleaned_df.columns.tolist()
        
        # Normalize column names
        cleaned_df.columns = [normalize_column_name(col) for col in cleaned_df.columns]
        
        # Log column transformations
        if self.verbose:
            self._log("\nColumn name transformations:")
            for orig, new in zip(original_columns, cleaned_df.columns):
                if orig != new:
                    self._log(f"  '{orig}' -> '{new}'")
        
        # Handle date columns
        self._process_date_columns(cleaned_df)
        
        return cleaned_df
    
    def _process_date_columns(self, df: pd.DataFrame):
        """
        Process date columns in the DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to process (modified in place)
        """
        # Find potential date columns
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        
        for date_col in date_columns:
            try:
                self._log(f"Processing date column: {date_col}")
                # Convert to datetime
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                self._log(f"  Converted to datetime: {df[date_col].dtype}")
                
                # Count null values after conversion
                null_count = df[date_col].isnull().sum()
                if null_count > 0:
                    self._log(f"  Warning: {null_count} invalid dates converted to NaT")
                    
            except Exception as e:
                self._log(f"  Error processing {date_col}: {e}")
    
    def get_data_summary(self, df: pd.DataFrame) -> dict:
        """
        Get a summary of the DataFrame.
        
        Args:
            df (pd.DataFrame): The DataFrame to summarize
            
        Returns:
            dict: Summary information
        """
        return {
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': df.dtypes.to_dict(),
            'null_counts': df.isnull().sum().to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum()
        }
    
    def print_data_summary(self, df: pd.DataFrame, title: str = "Data Summary"):
        """
        Print a formatted summary of the DataFrame.
        
        Args:
            df (pd.DataFrame): The DataFrame to summarize
            title (str): Title for the summary
        """
        if not self.verbose:
            return
            
        print(f"\n{title}")
        print("-" * len(title))
        print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"Columns: {list(df.columns)}")
        print(f"\nData types:")
        for col, dtype in df.dtypes.items():
            print(f"  {col}: {dtype}")
        
        # Show null counts if any
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            print(f"\nNull values:")
            for col, count in null_counts.items():
                if count > 0:
                    print(f"  {col}: {count}")
        
        print(f"\nSample data:")
        print(df.head(3).to_string())
