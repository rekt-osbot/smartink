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


def _safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return percentage change while guarding against zero denominators."""
    denominator_safe = denominator.replace({0: np.nan})
    return (numerator / denominator_safe) * 100


def _calculate_derived_metrics(df: pd.DataFrame, sma_label: str, prev_sma_label: str) -> pd.DataFrame:
    """Enrich the raw breakout dataset with derivative metrics used across the signal pipeline."""
    metrics = df.copy()
    if metrics.index.has_duplicates:
        # Downstream arithmetic expects row-wise alignment; duplicate indexes trigger
        # pandas' alignment safeguards and raise ``ValueError: cannot reindex on an axis
        # with duplicate labels``. A fresh default index preserves the row ordering while
        # guaranteeing uniqueness so element-wise math succeeds.
        metrics.reset_index(drop=True, inplace=True)
    metrics["trend_strength"] = _safe_pct(metrics["sma_20"] - metrics["sma_50"], metrics["sma_50"])
    metrics["trend_bias"] = np.select(
        [
            (metrics["sma_20"].notna()) & (metrics["sma_50"].notna()) & (metrics["sma_20"] > metrics["sma_50"]),
            (metrics["sma_20"].notna()) & (metrics["sma_50"].notna()) & (metrics["sma_20"] < metrics["sma_50"]),
        ],
        ["Bullish Bias", "Bearish Bias"],
        default="Neutral Bias",
    )
    metrics["rsi_signal"] = np.select(
        [metrics["rsi_14"].ge(60), metrics["rsi_14"].le(40), metrics["rsi_14"].isna()],
        ["Overbought", "Oversold", "No Signal"],
        default="Neutral",
    )

    metrics["percentage_from_sma"] = _safe_pct(metrics["close"] - metrics[sma_label], metrics[sma_label])
    metrics["prev_percentage_from_sma"] = _safe_pct(
        metrics["prev_close"] - metrics[prev_sma_label], metrics[prev_sma_label]
    )
    metrics["distance_change_pct"] = metrics["percentage_from_sma"] - metrics["prev_percentage_from_sma"]
    metrics["high_break_pct"] = _safe_pct(metrics["high"] - metrics[sma_label], metrics[sma_label])
    metrics["low_break_pct"] = _safe_pct(metrics["low"] - metrics[sma_label], metrics[sma_label])
    metrics["close_vs_prev_close_pct"] = _safe_pct(metrics["close"] - metrics["prev_close"], metrics["prev_close"])
    metrics["volume_surge_ratio"] = np.where(
        (metrics["avg_volume_5"].notna()) & (metrics["avg_volume_5"] > 0),
        metrics["volume"] / metrics["avg_volume_5"],
        np.nan,
    )
    metrics["momentum_5"] = _safe_pct(metrics["close"] - metrics["avg_close_5"], metrics["avg_close_5"])
    metrics["twenty_day_breakout_pct"] = _safe_pct(
        metrics["close"] - metrics["rolling_high_20"], metrics["rolling_high_20"]
    )

    small_tolerance = 0.1
    metrics["position_vs_sma"] = np.select(
        [
            metrics["percentage_from_sma"] > small_tolerance,
            metrics["percentage_from_sma"] < -small_tolerance,
        ],
        ["Above", "Below"],
        default="At",
    )

    return metrics


def _determine_breakout_conditions(metrics: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute the boolean masks representing mutually exclusive breakout scenarios."""
    breakout_confirm_pct = 0.35
    retest_buffer_pct = 0.6
    trigger_buffer_pct = 0.8
    small_tolerance = 0.1

    pct = metrics["percentage_from_sma"]
    prev_pct = metrics["prev_percentage_from_sma"]
    high_break = metrics["high_break_pct"]
    low_break = metrics["low_break_pct"]
    distance_change = metrics["distance_change_pct"].fillna(0)
    momentum = metrics["momentum_5"].fillna(0)

    fresh_breakout = (
        (pct >= breakout_confirm_pct)
        & (
            prev_pct.isna()
            | (prev_pct <= breakout_confirm_pct / 2)
            | (distance_change >= breakout_confirm_pct)
        )
    )

    fresh_breakdown = (
        (pct <= -breakout_confirm_pct)
        & (
            prev_pct.isna()
            | (prev_pct >= -breakout_confirm_pct / 2)
            | (distance_change <= -breakout_confirm_pct)
        )
    )

    retest_hold = (
        (pct > breakout_confirm_pct / 2)
        & (low_break >= -retest_buffer_pct)
        & (low_break <= breakout_confirm_pct)
        & (~fresh_breakout)
    )

    momentum_continuation = (
        (pct > breakout_confirm_pct / 2)
        & (prev_pct > breakout_confirm_pct / 2)
        & (distance_change > 0)
        & (momentum > 0)
        & (~fresh_breakout)
        & (~retest_hold)
    )

    failed_breakout = (pct < -small_tolerance) & (high_break >= breakout_confirm_pct) & (distance_change < 0)

    trigger_watch = (
        (pct >= -trigger_buffer_pct)
        & (pct <= breakout_confirm_pct)
        & (high_break >= -small_tolerance)
        & (~fresh_breakout)
        & (~retest_hold)
        & (~momentum_continuation)
    )

    bearish_drift = (pct < -small_tolerance) & (~fresh_breakdown) & (~failed_breakout)

    return {
        "fresh_breakout": fresh_breakout,
        "fresh_breakdown": fresh_breakdown,
        "retest_hold": retest_hold,
        "momentum_continuation": momentum_continuation,
        "failed_breakout": failed_breakout,
        "trigger_watch": trigger_watch,
        "bearish_drift": bearish_drift,
    }


def _assign_breakout_status(metrics: pd.DataFrame, conditions: Dict[str, pd.Series]) -> pd.DataFrame:
    """Attach human-readable status and signal labels based on detected scenarios."""
    labelled = metrics.copy()
    labelled["breakout_status"] = "At SMA"
    labelled.loc[labelled["position_vs_sma"] == "Above", "breakout_status"] = "Holding Above"
    labelled.loc[labelled["position_vs_sma"] == "Below", "breakout_status"] = "Holding Below"
    labelled.loc[conditions["fresh_breakout"], "breakout_status"] = "Fresh Breakout Above"
    labelled.loc[conditions["fresh_breakdown"], "breakout_status"] = "Fresh Breakdown Below"

    default_signal = "Range-Bound / No Signal"
    signal = np.array([default_signal] * len(labelled), dtype=object)
    pct = labelled["percentage_from_sma"]

    signal[conditions["fresh_breakout"]] = "Fresh Breakout (Confirmed)"
    signal[conditions["fresh_breakdown"]] = "Fresh Breakdown (Confirmed)"
    signal[conditions["retest_hold"]] = "Retest & Hold Above"
    signal[conditions["momentum_continuation"]] = "Momentum Continuation"
    signal[conditions["trigger_watch"] & (pct >= 0)] = "Breakout Watch (Compression)"
    signal[conditions["trigger_watch"] & (pct < 0)] = "Breakout Watch (Slightly Below)"
    signal[conditions["failed_breakout"]] = "Failed Breakout - Caution"
    signal[conditions["bearish_drift"] & (~conditions["fresh_breakdown"])] = "Bearish Drift / Breakdown Risk"

    labelled["breakout_signal"] = signal
    return labelled


def _calculate_confidence_score(labelled: pd.DataFrame, conditions: Dict[str, pd.Series]) -> np.ndarray:
    """
    Build the breakout confidence score.

    The score starts from a scenario-driven base value and then adds:
    * Proximity to the SMA (tighter closes boost above/below readings).
    * Volume surge: a 1x surge adds no points, while a 3x surge can add up to 15 points.
    * Short-term momentum: five-day momentum contributes up to +/-5 points.
    * Trend alignment: favour moves aligning with the 20/50 SMA relationship.
    * RSI extremes: penalise overbought conditions for long breakouts and oversold for breakdowns.
    """
    base = np.full(len(labelled), 40.0)
    pct = labelled["percentage_from_sma"]
    momentum = labelled["momentum_5"].fillna(0)

    base[conditions["fresh_breakout"]] = 70.0
    base[conditions["retest_hold"]] = 60.0
    base[conditions["momentum_continuation"]] = 55.0
    base[conditions["trigger_watch"] & (pct >= 0)] = 50.0
    base[conditions["trigger_watch"] & (pct < 0)] = 45.0
    base[conditions["failed_breakout"]] = 25.0
    base[conditions["fresh_breakdown"]] = 65.0
    base[conditions["bearish_drift"] & (~conditions["fresh_breakdown"])] = 45.0

    confidence = base.copy()
    confidence += np.clip(pct, -3, 3)

    vol_adj = np.clip(np.nan_to_num(labelled["volume_surge_ratio"], nan=1.0) - 1, -1, 3)
    confidence += vol_adj * 5

    confidence += np.clip(momentum / 2, -5, 5)

    if "trend_bias" in labelled.columns:
        confidence += np.where(labelled["trend_bias"] == "Bullish Bias", np.where(pct >= 0, 5, -5), 0)
        confidence += np.where(labelled["trend_bias"] == "Bearish Bias", np.where(pct < 0, 5, -5), 0)

    if "rsi_signal" in labelled.columns:
        confidence += np.where(labelled["rsi_signal"] == "Overbought", np.where(pct >= 0, -5, 5), 0)
        confidence += np.where(labelled["rsi_signal"] == "Oversold", np.where(pct < 0, -5, 5), 0)

    return np.clip(confidence, 0, 100)


def _select_and_rank_candidates(
    labelled: pd.DataFrame, conditions: Dict[str, pd.Series], max_distance: float
) -> pd.DataFrame:
    """Filter, sort, and present breakout candidates in priority order."""
    pct = labelled["percentage_from_sma"]
    signal_priority = np.full(len(labelled), 6.0)

    signal_priority[conditions["fresh_breakout"]] = 1.0
    signal_priority[conditions["retest_hold"]] = 2.0
    signal_priority[conditions["momentum_continuation"]] = 3.0
    signal_priority[conditions["trigger_watch"] & (pct >= 0)] = 3.5
    signal_priority[conditions["trigger_watch"] & (pct < 0)] = 4.0
    signal_priority[conditions["failed_breakout"]] = 4.5
    signal_priority[conditions["fresh_breakdown"]] = 1.5
    signal_priority[conditions["bearish_drift"] & (~conditions["fresh_breakdown"])] = 5.0

    selection_mask = (
        (pct.abs() <= max_distance)
        | conditions["fresh_breakout"]
        | conditions["fresh_breakdown"]
        | conditions["trigger_watch"]
        | conditions["failed_breakout"]
    )

    filtered = labelled.loc[selection_mask].copy()

    if filtered.empty:
        return filtered

    filtered.insert(0, "rank_priority", signal_priority[filtered.index])
    filtered = filtered.sort_values(
        by=["rank_priority", "breakout_confidence", "percentage_from_sma", "symbol"],
        ascending=[True, False, True, True],
    )
    filtered = filtered.drop(columns=["rank_priority"])
    return filtered.reset_index(drop=True)


def analyze_breakout_signals(
    breakout_df: Optional[pd.DataFrame], sma_period: int = 20, max_distance: float = 5.0
) -> Optional[pd.DataFrame]:
    """
    Transform enriched OHLCV data into actionable breakout insights.

    Args:
        breakout_df (Optional[pd.DataFrame]): Output from :meth:`StockDataManager.get_stocks_near_sma_breakout`.
        sma_period (int): Focus SMA period (matches the query that produced the snapshot).
        max_distance (float): Maximum allowed percentage distance from the SMA for neutral candidates.

    Returns:
        Optional[pd.DataFrame]: Ranked breakout candidates with status, signal, and confidence columns.
    """
    if breakout_df is None:
        return None
    if breakout_df.empty:
        return breakout_df

    sma_label = f"sma_{sma_period}"
    prev_sma_label = f"prev_sma_{sma_period}"

    metrics = _calculate_derived_metrics(breakout_df, sma_label, prev_sma_label)
    conditions = _determine_breakout_conditions(metrics)
    labelled = _assign_breakout_status(metrics, conditions)
    labelled["breakout_confidence"] = _calculate_confidence_score(labelled, conditions)

    return _select_and_rank_candidates(labelled, conditions, max_distance)


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
        raw_snapshot = self.data_manager.get_stocks_near_sma_breakout(sma_period, max_distance)
        return analyze_breakout_signals(raw_snapshot, sma_period=sma_period, max_distance=max_distance)

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
