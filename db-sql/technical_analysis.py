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
from config import CONSOLE_WIDTH


class TechnicalAnalyzer:
    """Handles technical analysis and stock screening."""
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the technical analyzer.
        
        Args:
            verbose (bool): Whether to print detailed logs
        """
        self.verbose = verbose
        self.fetcher = StockDataFetcher(verbose=verbose)
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
    
    def fetch_and_store_data(self, symbols: List[str] = None, period: str = "3mo", use_popular_only: bool = False, max_stocks: int = None, progress_callback=None) -> bool:
        """
        Fetch stock data and store in database.

        Args:
            symbols (List[str], optional): List of symbols to fetch. If None, gets from database
            period (str): Period for data fetching
            use_popular_only (bool): If True, use only popular stocks that work well with yfinance
            max_stocks (int, optional): Maximum number of stocks to fetch. If None, fetches all

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
            total_records = 0
            total_processed = 0

            for batch_start in range(0, len(symbols), batch_size):
                batch_end = min(batch_start + batch_size, len(symbols))
                batch_symbols = symbols[batch_start:batch_end]

                self._log(f"Processing batch {batch_start//batch_size + 1}: symbols {batch_start+1}-{batch_end}")

                # Fetch data for this batch
                stock_data = self.fetcher.fetch_multiple_stocks(batch_symbols, period)

                if not stock_data:
                    self._log(f"No data fetched for batch {batch_start//batch_size + 1}")
                    continue

                # Store price data and indicators for this batch
                batch_records = 0
                for symbol, data in stock_data.items():
                    if data is not None and not data.empty:
                        # Store price data
                        if self.data_manager.insert_price_data(data):
                            batch_records += len(data)

                        # Store indicators data (SMA is already calculated)
                        indicators_data = data[['symbol', 'date', 'sma_20']].copy()
                        self.data_manager.insert_indicators_data(indicators_data)

                total_records += batch_records
                total_processed += len(stock_data)

                self._log(f"✓ Batch {batch_start//batch_size + 1} completed: {batch_records} records for {len(stock_data)} stocks")

                # Clear batch data from memory
                del stock_data

                # Small pause between batches to allow garbage collection
                import time
                time.sleep(0.5)

            self._log(f"✓ Successfully stored {total_records} price records for {total_processed} stocks")
            return True
            
        except Exception as e:
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

        # Format the data for display
        display_data = []
        for _, row in stocks.iterrows():
            # Color coding for breakout status
            status_symbol = "🟢" if "Above" in row['breakout_status'] else "🔴" if "Below" in row['breakout_status'] else "⚪"

            display_data.append([
                row['symbol'],
                f"{row['close']:.2f}",
                f"{row[f'sma_{sma_period}']:.2f}",
                f"{row['percentage_from_sma']:+.2f}%",
                f"{status_symbol} {row['breakout_status']}",
                row['date']
            ])

        headers = ['Symbol', 'Current Price', f'{sma_period}-Day SMA', '% From SMA', 'Breakout Status', 'Date']
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

        # Format the data for display
        display_data = []
        for _, row in stocks.iterrows():
            display_data.append([
                row['symbol'],
                f"{row['close']:.2f}",
                f"{row[f'sma_{sma_period}']:.2f}",
                f"{row['percentage_above_sma']:.2f}%",
                row['date']
            ])

        headers = ['Symbol', 'Current Price', f'{sma_period}-Day SMA', '% Above SMA', 'Date']
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
        
        # Format the data for display
        display_data = []
        for _, row in patterns.iterrows():
            display_data.append([
                row['symbol'],
                row['yesterday_date'],
                f"{row['yesterday_open']:.2f}",
                f"{row['yesterday_high']:.2f}",
                row['today_date'],
                f"{row['today_close']:.2f}",
                f"{row['breakout_percentage']:.2f}%"
            ])
        
        headers = [
            'Symbol', 
            'Yesterday Date', 
            'Yesterday Open', 
            'Yesterday High',
            'Today Date',
            'Today Close',
            'Breakout %'
        ]
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
            
        except Exception as e:
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
            
        except Exception as e:
            self._log(f"Error exporting results: {e}")
            return False
