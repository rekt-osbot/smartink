"""
Technical analysis module for stock screening and pattern detection.
This module provides functions to analyze stock data and identify trading opportunities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from tabulate import tabulate

from stock_data_fetcher import StockDataFetcher
from stock_data_manager import StockDataManager
from utils import print_step, print_section_header
from config import CONSOLE_WIDTH, PRIMARY_CSV_URL, BHAV_CSV_URL
from data_processor import DataProcessor


class TechnicalAnalyzer:
    """Handles technical analysis and stock screening."""
    
    def __init__(self, verbose: bool = True, use_filtering: bool = True):
        """
        Initialize the technical analyzer.

        Args:
            verbose (bool): Whether to print detailed logs
            use_filtering (bool): Whether to enable smart stock filtering
        """
        self.verbose = verbose
        self.use_filtering = use_filtering
        self.fetcher = StockDataFetcher(verbose=verbose, use_filtering=use_filtering)
        self.data_manager = StockDataManager(verbose=verbose)
    
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def setup_database(self) -> bool:
        """
        Set up the extended database schema.

        Returns:
            bool: True if successful
        """
        return self.data_manager.setup_extended_schema()

    def refresh_master_stock_list(self) -> bool:
        """
        Fetches the latest list of all tradable stocks from NSE's primary source
        and rebuilds the main 'tradable_stocks' table.

        Returns:
            bool: True if successful
        """
        self._log("Attempting to refresh the master stock list from NSE...")

        # We need a DataProcessor instance to fetch and clean the master list
        data_processor = DataProcessor(verbose=self.verbose)

        self._log(f"Fetching master list from primary source: {PRIMARY_CSV_URL}")
        df = data_processor.load_csv_from_url(PRIMARY_CSV_URL)

        # Fallback if the primary URL fails
        if df is None:
            self._log(f"Primary source failed. Trying fallback: {BHAV_CSV_URL}")
            df = data_processor.load_csv_from_url(BHAV_CSV_URL)

        if df is None:
            self._log("✗ Failed to fetch master stock list from any online source.")
            return False

        self._log("✓ Master list data fetched successfully. Cleaning data...")
        cleaned_df = data_processor.clean_dataframe(df)

        self._log("Rebuilding the 'tradable_stocks' table with fresh data...")
        # Use the analyzer's own data_manager to perform the update
        success = self.data_manager.create_and_populate_table(cleaned_df)

        if success:
            self._log(f"✓ Master stock list updated successfully with {len(cleaned_df)} stocks.")
        else:
            self._log("✗ Failed to update the master stock list in the database.")

        return success
    
    def fetch_and_store_data(self, symbols: List[str] = None, period: str = "3mo", use_popular_only: bool = False, max_stocks: int = None, progress_callback=None) -> bool:
        """
        Fetch stock data and store in database.

        Args:
            symbols (List[str], optional): List of symbols to fetch. If None, gets from database
            period (str): Period for data fetching
            use_popular_only (bool): If True, use only popular stocks that work well with yfinance
            max_stocks (int, optional): Maximum number of stocks to fetch. If None, fetches all
            progress_callback (function, optional): Callback for progress updates

        Returns:
            bool: True if successful
        """
        try:
            if symbols is None:
                if use_popular_only:
                    # Use popular stocks that are known to work with yfinance
                    symbols = self.fetcher.get_stocks_from_database(use_popular_only=True)
                    if not symbols:
                        # Fallback to hardcoded popular stocks
                        symbols = self.fetcher.get_popular_nse_stocks()
                        self._log("Using hardcoded popular stocks as fallback")
                else:
                    # Get ALL stocks from database
                    symbols = self.fetcher.get_stocks_from_database()

                if not symbols:
                    self._log("No symbols found")
                    return False

            # Apply max_stocks limit if specified
            if max_stocks and len(symbols) > max_stocks:
                self._log(f"Limiting to first {max_stocks} stocks out of {len(symbols)}")
                symbols = symbols[:max_stocks]
            else:
                self._log(f"Fetching data for all {len(symbols)} stocks from database")

            self._log(f"Fetching data for {len(symbols)} stocks...")

            # Process stocks in memory-efficient batches
            batch_size = 100  # Process 100 stocks at a time
            all_price_data = []
            all_indicators_data = []
            total_processed = 0

            for batch_start in range(0, len(symbols), batch_size):
                batch_end = min(batch_start + batch_size, len(symbols))
                batch_symbols = symbols[batch_start:batch_end]

                self._log(f"Processing batch {batch_start//batch_size + 1}: symbols {batch_start+1}-{batch_end}")

                # Fetch data for this batch
                stock_data = self.fetcher.fetch_multiple_stocks(batch_symbols, period)

                if not stock_data:
                    self._log(f"No data fetched for batch {batch_start//batch_size + 1}")
                    if progress_callback:
                        progress = (batch_end / len(symbols))
                        progress_callback(progress, f"Batch {batch_start//batch_size + 1} failed, skipping...")
                    continue

                # Collect price and indicators data for this batch
                for symbol, data in stock_data.items():
                    if data is not None and not data.empty:
                        all_price_data.append(data)
                        all_indicators_data.append(data[['symbol', 'date', 'sma_20']].copy())

                total_processed += len(stock_data)
                self._log(f"✓ Batch {batch_start//batch_size + 1} completed for {len(stock_data)} stocks")

                # Update progress
                if progress_callback:
                    progress = (batch_end / len(symbols))
                    progress_callback(progress, f"Processed {batch_end}/{len(symbols)} symbols...")

                # Clear batch data from memory
                del stock_data

            if not all_price_data:
                self._log("No data collected to store.")
                return True

            # Bulk insert all collected data
            self._log("Starting bulk insert of all collected data...")
            price_df = pd.concat(all_price_data)
            indicators_df = pd.concat(all_indicators_data)

            price_success = self.data_manager.insert_price_data(price_df)
            indicators_success = self.data_manager.insert_indicators_data(indicators_df)

            if price_success and indicators_success:
                self._log(f"✓ Successfully stored {len(price_df)} price records and {len(indicators_df)} indicator records for {total_processed} stocks")
                return True
            else:
                self._log("✗ Bulk insert failed.")
                return False

        except (sqlite3.Error, IOError, KeyError) as e:
            self._log(f"Error fetching and storing data: {e}")
            return False
    
    def get_stocks_near_sma_breakout(self, sma_period: int = 20, max_distance: float = 5.0) -> Optional[pd.DataFrame]:
        """
        Get stocks near SMA that are breaking out (actionable opportunities).

        Args:
            sma_period (int): SMA period
            max_distance (float): Maximum percentage distance from SMA

        Returns:
            Optional[pd.DataFrame]: Stocks near SMA breakout or None
        """
        return self.data_manager.get_stocks_near_sma_breakout(sma_period, max_distance)

    def get_stocks_above_sma(self, sma_period: int = 20, max_distance: float = None) -> Optional[pd.DataFrame]:
        """
        Get stocks currently trading above their SMA.

        Args:
            sma_period (int): SMA period
            max_distance (float): Maximum percentage above SMA (None for no limit)

        Returns:
            Optional[pd.DataFrame]: Filtered stocks or None
        """
        return self.data_manager.get_stocks_above_sma(sma_period, max_distance)
    
    def get_open_high_patterns(self) -> Optional[pd.DataFrame]:
        """
        Get stocks with open=high patterns.
        
        Returns:
            Optional[pd.DataFrame]: Stocks with patterns or None
        """
        return self.data_manager.get_open_high_patterns()
    
    def format_stocks_for_display(self, stocks: pd.DataFrame, headers: List[str]) -> List[List[str]]:
        """Format a DataFrame of stocks for display in a table."""
        display_data = []
        if stocks is None or stocks.empty:
            return display_data

        for _, row in stocks.iterrows():
            row_data = []
            for header in headers:
                col_name = header.lower().replace(' ', '_')
                if col_name in row:
                    value = row[col_name]
                    if isinstance(value, float):
                        row_data.append(f"{value:.2f}")
                    else:
                        row_data.append(str(value))
                else:
                    row_data.append("")
            display_data.append(row_data)
        return display_data

    def display_stocks_near_sma_breakout(self, sma_period: int = 20, max_distance: float = 5.0):
        """
        Display stocks near SMA breakout in a formatted table (actionable opportunities).

        Args:
            sma_period (int): SMA period
            max_distance (float): Maximum percentage distance from SMA
        """
        print_section_header(f"STOCKS NEAR {sma_period}-DAY SMA BREAKOUT (±{max_distance}%)", CONSOLE_WIDTH)

        stocks = self.get_stocks_near_sma_breakout(sma_period, max_distance)

        if stocks is None or stocks.empty:
            print("No stocks found near SMA breakout or no data available.")
            print("Try running 'Fetch Latest Data' first.")
            return

        stocks_to_display = stocks.copy()
        stocks_to_display['breakout_status'] = stocks_to_display.apply(
            lambda row: f"{'🟢' if 'Above' in row['breakout_status'] else '🔴' if 'Below' in row['breakout_status'] else '⚪'} {row['breakout_status']}",
            axis=1
        )
        stocks_to_display['percentage_from_sma'] = stocks_to_display['percentage_from_sma'].map('{:+.2f}%'.format)


        headers = ['Symbol', 'Close', f'sma_{sma_period}', 'percentage_from_sma', 'breakout_status', 'Date']

        display_data = self.format_stocks_for_display(stocks_to_display, headers)

        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal actionable stocks near {sma_period}-day SMA: {len(display_data)}")

        # Show breakdown by status
        status_counts = stocks['breakout_status'].value_counts()
        print(f"\nBreakdown:")
        for status, count in status_counts.items():
            print(f"• {status}: {count} stocks")

    def display_stocks_above_sma(self, sma_period: int = 20, max_distance: float = None):
        """
        Display stocks above SMA in a formatted table.

        Args:
            sma_period (int): SMA period
            max_distance (float): Maximum percentage above SMA (None for no limit)
        """
        title = f"STOCKS ABOVE {sma_period}-DAY SMA"
        if max_distance:
            title += f" (≤{max_distance}%)"

        print_section_header(title, CONSOLE_WIDTH)

        stocks = self.get_stocks_above_sma(sma_period, max_distance)

        if stocks is None or stocks.empty:
            print("No stocks found above SMA or no data available.")
            print("Try running 'Fetch Latest Data' first.")
            return

        stocks_to_display = stocks.copy()
        stocks_to_display['percentage_above_sma'] = stocks_to_display['percentage_above_sma'].map('{:.2f}%'.format)

        headers = ['Symbol', 'Close', f'sma_{sma_period}', 'percentage_above_sma', 'Date']

        display_data = self.format_stocks_for_display(stocks_to_display, headers)

        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal stocks above {sma_period}-day SMA: {len(display_data)}")
    
    def display_open_high_patterns(self):
        """Display stocks with open=high patterns in a formatted table."""
        print_section_header("OPEN = HIGH BREAKOUT PATTERNS", CONSOLE_WIDTH)
        
        patterns = self.get_open_high_patterns()
        
        if patterns is None or patterns.empty:
            print("No open=high patterns found or no data available.")
            print("Try running 'Fetch Latest Data' first.")
            return
        
        patterns_to_display = patterns.copy()
        patterns_to_display['breakout_percentage'] = patterns_to_display['breakout_percentage'].map('{:.2f}%'.format)

        headers = [
            'Symbol', 
            'yesterday_date',
            'yesterday_open',
            'yesterday_high',
            'today_date',
            'today_close',
            'breakout_percentage'
        ]

        display_data = self.format_stocks_for_display(patterns_to_display, headers)

        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal stocks with open=high patterns: {len(display_data)}")
    
    def get_summary_statistics(self) -> Dict[str, int]:
        """
        Get summary statistics for the analysis.
        
        Returns:
            Dict[str, int]: Summary statistics
        """
        try:
            stats = {}
            
            # Count stocks above SMA
            stocks_above_sma = self.get_stocks_above_sma(20)
            stats['stocks_above_20_sma'] = len(stocks_above_sma) if stocks_above_sma is not None else 0
            
            # Count open=high patterns
            open_high_patterns = self.get_open_high_patterns()
            stats['open_high_patterns'] = len(open_high_patterns) if open_high_patterns is not None else 0
            
            # Count total stocks with data
            latest_prices = self.data_manager.get_latest_prices(limit=10000)
            if latest_prices is not None:
                stats['total_stocks_with_data'] = latest_prices['symbol'].nunique()
            else:
                stats['total_stocks_with_data'] = 0
            
            return stats
            
        except (sqlite3.Error, KeyError) as e:
            self._log(f"Error getting summary statistics: {e}")
            return {}
    
    def display_summary(self):
        """Display summary statistics."""
        print_section_header("TECHNICAL ANALYSIS SUMMARY", CONSOLE_WIDTH)
        
        stats = self.get_summary_statistics()
        
        if not stats:
            print("No statistics available. Try fetching data first.")
            return
        
        summary_data = [
            ['Total Stocks with Data', stats.get('total_stocks_with_data', 0)],
            ['Stocks Above 20-Day SMA', stats.get('stocks_above_20_sma', 0)],
            ['Open=High Breakout Patterns', stats.get('open_high_patterns', 0)]
        ]
        
        print(tabulate(summary_data, headers=['Metric', 'Count'], tablefmt="grid"))
        
        # Calculate percentages if we have data
        total = stats.get('total_stocks_with_data', 0)
        if total > 0:
            sma_percentage = (stats.get('stocks_above_20_sma', 0) / total) * 100
            pattern_percentage = (stats.get('open_high_patterns', 0) / total) * 100
            
            print(f"\nPercentages:")
            print(f"• {sma_percentage:.1f}% of stocks are above 20-day SMA")
            print(f"• {pattern_percentage:.1f}% of stocks show open=high patterns")
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """
        Clean up old data to keep database size manageable.
        
        Args:
            days_to_keep (int): Number of days to keep
            
        Returns:
            bool: True if successful
        """
        return self.data_manager.cleanup_old_data(days_to_keep)
    
    def export_results_to_csv(self, output_dir: str = ".") -> bool:
        """
        Export analysis results to CSV files.
        
        Args:
            output_dir (str): Directory to save CSV files
            
        Returns:
            bool: True if successful
        """
        try:
            from pathlib import Path
            output_path = Path(output_dir)
            
            # Export stocks above SMA
            stocks_above_sma = self.get_stocks_above_sma(20)
            if stocks_above_sma is not None and not stocks_above_sma.empty:
                sma_file = output_path / "stocks_above_20_sma.csv"
                stocks_above_sma.to_csv(sma_file, index=False)
                self._log(f"Exported stocks above SMA to {sma_file}")
            
            # Export open=high patterns
            open_high_patterns = self.get_open_high_patterns()
            if open_high_patterns is not None and not open_high_patterns.empty:
                patterns_file = output_path / "open_high_patterns.csv"
                open_high_patterns.to_csv(patterns_file, index=False)
                self._log(f"Exported open=high patterns to {patterns_file}")
            
            return True
            
        except IOError as e:
            self._log(f"Error exporting results: {e}")
            return False
