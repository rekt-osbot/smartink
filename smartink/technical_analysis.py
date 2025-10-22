"""
Technical analysis module for stock screening and pattern detection.
This module provides functions to analyze stock data and identify trading opportunities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from tabulate import tabulate

from smartink.stock_data_fetcher import StockDataFetcher
from smartink.stock_data_manager import StockDataManager
from smartink.utils import print_step, print_section_header
from smartink.config import CONSOLE_WIDTH, PRIMARY_CSV_URL, BHAV_CSV_URL
from smartink.data_processor import DataProcessor


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
        from smartink.database_manager import DatabaseManager
        db_manager = DatabaseManager(verbose=self.verbose)
        success = db_manager.create_and_populate_table(cleaned_df)

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
                        indicator_columns = ['symbol', 'date']
                        for column in ['sma_20', 'sma_50', 'rsi_14']:
                            if column in data.columns:
                                indicator_columns.append(column)

                        indicators_data = data[indicator_columns].copy()
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
        def format_number(value, decimals=2, signed=False, suffix=""):
            if pd.isna(value):
                return "—"
            fmt = f"{{:{'+' if signed else ''}.{decimals}f}}"
            return fmt.format(value) + suffix

        def format_ratio(value):
            if pd.isna(value):
                return "—"
            return f"{value:.2f}x"

        display_data = []
        for _, row in stocks.iterrows():
            status_symbol = "🟢" if "Above" in row['breakout_status'] else "🔴" if "Below" in row['breakout_status'] else "⚪"
            signal_symbol_map = {
                'Fresh Breakout (Confirmed)': '🚀',
                'Retest & Hold Above': '🛡️',
                'Momentum Continuation': '📈',
                'Breakout Watch (Compression)': '⏳',
                'Breakout Watch (Slightly Below)': '👀',
                'Failed Breakout - Caution': '⚠️',
                'Fresh Breakdown (Confirmed)': '⛔',
                'Bearish Drift / Breakdown Risk': '📉',
                'Range-Bound / No Signal': '➖'
            }
            signal_label = row.get('breakout_signal', 'Range-Bound / No Signal')
            signal_display = f"{signal_symbol_map.get(signal_label, '➖')} {signal_label}"

            confidence_display = format_number(row.get('breakout_confidence'), decimals=0)

            display_data.append([
                row['symbol'],
                format_number(row['close']),
                format_number(row.get('sma_20'), suffix=""),
                format_number(row.get('sma_50'), suffix=""),
                format_number(row.get('percentage_from_sma'), signed=True, suffix="%"),
                row.get('trend_bias', 'Neutral Bias'),
                format_number(row.get('trend_strength'), signed=True, suffix="%"),
                format_number(row.get('rsi_14'), decimals=1),
                row.get('rsi_signal', 'Neutral'),
                f"{status_symbol} {row['breakout_status']}",
                signal_display,
                confidence_display,
                format_ratio(row.get('volume_surge_ratio')),
                format_number(row.get('momentum_5'), signed=True, suffix="%"),
                row['date']
            ])

        headers = [
            'Symbol',
            'Close',
            '20-Day SMA',
            '50-Day SMA',
            f'% vs {sma_period}-SMA',
            'Trend Bias',
            'Trend Δ (20-50)',
            'RSI(14)',
            'RSI Signal',
            'Breakout Status',
            'Breakout Signal',
            'Confidence',
            'Vol Surge (x)',
            '5D Momentum',
            'Date'
        ]
        print(tabulate(display_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal actionable stocks near {sma_period}-day SMA: {len(display_data)}")

        # Show breakdown by status
        status_counts = stocks['breakout_status'].value_counts()
        print(f"\nBreakdown:")
        for status, count in status_counts.items():
            print(f"• {status}: {count} stocks")

        if 'breakout_signal' in stocks.columns:
            signal_counts = stocks['breakout_signal'].value_counts()
            print("\nSignals:")
            for signal_name, count in signal_counts.items():
                print(f"• {signal_name}: {count} stocks")

        if 'breakout_confidence' in stocks.columns:
            avg_conf = stocks['breakout_confidence'].mean()
            high_conf = (stocks['breakout_confidence'] >= 70).sum()
            print(f"\nAverage breakout confidence: {avg_conf:.1f} / 100")
            print(f"High-conviction setups (≥70): {high_conf}")

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

        def format_number(value, decimals=2, signed=False, suffix=""):
            if pd.isna(value):
                return "—"
            fmt = f"{{:{'+' if signed else ''}.{decimals}f}}"
            return fmt.format(value) + suffix

        display_data = []
        for _, row in stocks.iterrows():
            display_data.append([
                row['symbol'],
                format_number(row['close']),
                format_number(row.get('sma_20'), suffix=""),
                format_number(row.get('sma_50'), suffix=""),
                format_number(row.get('percentage_above_sma'), signed=True, suffix="%"),
                row.get('trend_bias', 'Neutral Bias'),
                format_number(row.get('trend_strength'), signed=True, suffix="%"),
                format_number(row.get('rsi_14'), decimals=1),
                row.get('rsi_signal', 'Neutral'),
                row['date']
            ])

        headers = [
            'Symbol',
            'Close',
            '20-Day SMA',
            '50-Day SMA',
            f'% vs {sma_period}-SMA',
            'Trend Bias',
            'Trend Δ (20-50)',
            'RSI(14)',
            'RSI Signal',
            'Date'
        ]
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
        def format_number(value, decimals=2, signed=False, suffix=""):
            if pd.isna(value):
                return "—"
            fmt = f"{{:{'+' if signed else ''}.{decimals}f}}"
            return fmt.format(value) + suffix

        display_data = []
        for _, row in patterns.iterrows():
            display_data.append([
                row['symbol'],
                row['yesterday_date'],
                f"{row['yesterday_open']:.2f}",
                f"{row['yesterday_high']:.2f}",
                row['today_date'],
                f"{row['today_close']:.2f}",
                format_number(row.get('breakout_percentage'), signed=True, suffix="%"),
                row.get('trend_bias', 'Neutral Bias'),
                format_number(row.get('trend_strength'), signed=True, suffix="%"),
                format_number(row.get('rsi_14'), decimals=1),
                row.get('rsi_signal', 'Neutral')
            ])

        headers = [
            'Symbol',
            'Yesterday Date',
            'Yesterday Open',
            'Yesterday High',
            'Today Date',
            'Today Close',
            'Breakout %',
            'Trend Bias',
            'Trend Δ (20-50)',
            'RSI(14)',
            'RSI Signal'
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

            # Count stocks above 20-day SMA using efficient SQL query
            stats['stocks_above_20_sma'] = self.data_manager.count_stocks_above_sma(20)

            # Count open=high breakout patterns
            stats['open_high_patterns'] = self.data_manager.count_open_high_patterns()

            # Count total stocks with recent price data
            stats['total_stocks_with_data'] = self.data_manager.count_total_stocks_with_data()

            # Enrich with broader market diagnostics
            market_snapshot = self.data_manager.get_market_health_snapshot()
            if market_snapshot:
                stats['market_snapshot'] = market_snapshot
                stats['stocks_above_50_sma'] = market_snapshot.get('above_sma_50', 0)
                stats['bullish_trend'] = market_snapshot.get('bullish_trend', 0)
                stats['bearish_trend'] = market_snapshot.get('bearish_trend', 0)
                stats['neutral_trend'] = market_snapshot.get('neutral_trend', 0)
                stats['rsi_overbought'] = market_snapshot.get('rsi_overbought', 0)
                stats['rsi_oversold'] = market_snapshot.get('rsi_oversold', 0)
                stats['avg_rsi'] = market_snapshot.get('avg_rsi')
                stats['avg_trend_strength'] = market_snapshot.get('avg_trend_strength')

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
            ['Stocks Above 50-Day SMA', stats.get('stocks_above_50_sma', 0)],
            ['Bullish Trend Bias (20>50)', stats.get('bullish_trend', 0)],
            ['Bearish Trend Bias (20<50)', stats.get('bearish_trend', 0)],
            ['RSI Overbought (>=60)', stats.get('rsi_overbought', 0)],
            ['RSI Oversold (<=40)', stats.get('rsi_oversold', 0)],
            ['Open=High Breakout Patterns', stats.get('open_high_patterns', 0)]
        ]

        print(tabulate(summary_data, headers=['Metric', 'Count'], tablefmt="grid"))

        total = stats.get('total_stocks_with_data', 0)
        if total > 0:
            print("\nPercentages:")
            print(f"• {stats.get('stocks_above_20_sma', 0) / total * 100:.1f}% of stocks are above the 20-day SMA")
            if 'stocks_above_50_sma' in stats:
                print(f"• {stats.get('stocks_above_50_sma', 0) / total * 100:.1f}% of stocks are above the 50-day SMA")
            if 'bullish_trend' in stats and 'bearish_trend' in stats:
                bullish_ratio = stats.get('bullish_trend', 0) / total * 100
                bearish_ratio = stats.get('bearish_trend', 0) / total * 100
                print(f"• Trend bias: {bullish_ratio:.1f}% bullish vs {bearish_ratio:.1f}% bearish")
            print(f"• {stats.get('open_high_patterns', 0) / total * 100:.1f}% of stocks show open=high breakouts")

        avg_rsi = stats.get('avg_rsi')
        if avg_rsi is not None:
            print(f"Average RSI(14): {avg_rsi:.1f}")

        avg_trend_strength = stats.get('avg_trend_strength')
        if avg_trend_strength is not None:
            print(f"Average 20-50 SMA spread: {avg_trend_strength:+.2f}%")

        if total > 0 and 'bullish_trend' in stats and 'bearish_trend' in stats:
            breadth_score = (stats.get('bullish_trend', 0) - stats.get('bearish_trend', 0)) / total * 100
            print(f"Trend breadth score: {breadth_score:+.1f}")

    def display_market_health(self, rsi_overbought: float = 60.0, rsi_oversold: float = 40.0):
        """Present a consolidated market health snapshot."""
        print_section_header("MARKET HEALTH SNAPSHOT", CONSOLE_WIDTH)

        snapshot = self.data_manager.get_market_health_snapshot(rsi_overbought, rsi_oversold)

        if not snapshot:
            print("No market health data available. Try fetching data first.")
            return

        total = snapshot.get('total_stocks', 0)

        def with_percentage(count: int) -> str:
            if total <= 0:
                return str(count)
            return f"{count} ({count / total * 100:.1f}%)"

        rows = [
            ['Total Stocks', total],
            ['Above 20-Day SMA', with_percentage(snapshot.get('above_sma_20', 0))],
            ['Above 50-Day SMA', with_percentage(snapshot.get('above_sma_50', 0))],
            ['Bullish Trend Bias (20>50)', with_percentage(snapshot.get('bullish_trend', 0))],
            ['Bearish Trend Bias (20<50)', with_percentage(snapshot.get('bearish_trend', 0))],
            ['Neutral Trend Bias', with_percentage(snapshot.get('neutral_trend', 0))],
            ['RSI Overbought (>=60)', with_percentage(snapshot.get('rsi_overbought', 0))],
            ['RSI Oversold (<=40)', with_percentage(snapshot.get('rsi_oversold', 0))],
        ]

        print(tabulate(rows, headers=['Metric', 'Value'], tablefmt="grid"))

        avg_rsi = snapshot.get('avg_rsi')
        if avg_rsi is not None:
            print(f"Average RSI(14): {avg_rsi:.1f}")

        avg_trend_strength = snapshot.get('avg_trend_strength')
        if avg_trend_strength is not None:
            print(f"Average 20-50 SMA spread: {avg_trend_strength:+.2f}%")

        if total > 0:
            breadth_score = (snapshot.get('bullish_trend', 0) - snapshot.get('bearish_trend', 0)) / total * 100
            print(f"Trend breadth score: {breadth_score:+.1f}")
    
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
