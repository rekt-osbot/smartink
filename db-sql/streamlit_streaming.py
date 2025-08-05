"""
Streamlit streaming utilities for real-time progress updates.
"""

import streamlit as st
import time
from typing import Dict, Any, Optional


class StreamingProgressTracker:
    """Real-time progress tracker for Streamlit apps."""
    
    def __init__(self, total_items: int, title: str = "Processing"):
        """
        Initialize the progress tracker.
        
        Args:
            total_items (int): Total number of items to process
            title (str): Title for the progress display
        """
        self.total_items = total_items
        self.title = title
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.current_batch = 0
        self.total_batches = 0
        
        # Create UI containers
        self.header_container = st.container()
        self.progress_container = st.container()
        self.metrics_container = st.container()
        self.status_container = st.container()
        
        # Initialize UI elements
        with self.header_container:
            st.markdown(f"### {title}")
        
        with self.progress_container:
            self.progress_bar = st.progress(0)
            self.progress_text = st.empty()
        
        with self.metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                self.processed_metric = st.empty()
            with col2:
                self.successful_metric = st.empty()
            with col3:
                self.failed_metric = st.empty()
            with col4:
                self.rate_metric = st.empty()
        
        with self.status_container:
            self.status_text = st.empty()
            self.batch_text = st.empty()
        
        self.start_time = time.time()
        self._update_display()
    
    def start_batch(self, batch_num: int, total_batches: int, batch_info: str = ""):
        """Start processing a new batch."""
        self.current_batch = batch_num
        self.total_batches = total_batches
        
        batch_text = f"🔄 **Batch {batch_num}/{total_batches}**"
        if batch_info:
            batch_text += f" - {batch_info}"
        
        self.batch_text.markdown(batch_text)
        self._update_display()
    
    def update_progress(self, processed: int = None, successful: int = None, failed: int = None, status: str = None):
        """Update progress metrics."""
        if processed is not None:
            self.processed = processed
        if successful is not None:
            self.successful = successful
        if failed is not None:
            self.failed = failed
        
        if status:
            self.status_text.markdown(f"📊 {status}")
        
        self._update_display()
    
    def increment(self, success: bool = True, status: str = None):
        """Increment counters."""
        self.processed += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1
        
        if status:
            self.status_text.markdown(f"📊 {status}")
        
        self._update_display()
    
    def _update_display(self):
        """Update all display elements."""
        # Calculate progress percentage
        if self.total_items > 0:
            progress = min(self.processed / self.total_items, 1.0)
        else:
            progress = 0
        
        # Update progress bar
        self.progress_bar.progress(progress)
        
        # Update progress text
        self.progress_text.markdown(f"**Progress: {self.processed}/{self.total_items} ({progress*100:.1f}%)**")
        
        # Update metrics
        self.processed_metric.metric("📊 Processed", self.processed)
        self.successful_metric.metric("✅ Successful", self.successful)
        self.failed_metric.metric("❌ Failed", self.failed)
        
        # Calculate and display rate
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0 and self.processed > 0:
            rate = self.processed / elapsed_time
            self.rate_metric.metric("⚡ Rate", f"{rate:.1f}/sec")
        else:
            self.rate_metric.metric("⚡ Rate", "0.0/sec")
    
    def complete(self, final_message: str = None):
        """Mark processing as complete."""
        self.progress_bar.progress(1.0)
        
        if final_message:
            self.status_text.markdown(f"✅ **{final_message}**")
        else:
            success_rate = (self.successful / self.processed * 100) if self.processed > 0 else 0
            self.status_text.markdown(f"✅ **Completed! Success rate: {success_rate:.1f}%**")
        
        self.batch_text.empty()
        
        # Show final metrics
        elapsed_time = time.time() - self.start_time
        st.success(f"🎉 Processing completed in {elapsed_time:.1f} seconds!")
    
    def cleanup(self, delay: float = 2.0):
        """Clean up UI elements after a delay."""
        time.sleep(delay)
        try:
            self.header_container.empty()
            self.progress_container.empty()
            self.metrics_container.empty()
            self.status_container.empty()
        except:
            pass


def stream_stock_data_fetch(analyzer, use_popular_only=False, max_stocks=None):
    """
    Stream stock data fetching with real-time progress updates.
    
    Args:
        analyzer: TechnicalAnalyzer instance
        use_popular_only (bool): Whether to use only popular stocks
        max_stocks (int): Maximum number of stocks to fetch
    
    Returns:
        bool: True if successful
    """
    try:
        # Get symbols to process
        if use_popular_only:
            symbols = analyzer.fetcher.get_stocks_from_database(use_popular_only=True)
            if not symbols:
                symbols = analyzer.fetcher.get_popular_nse_stocks()
        else:
            symbols = analyzer.fetcher.get_stocks_from_database()
        
        if max_stocks and len(symbols) > max_stocks:
            symbols = symbols[:max_stocks]
        
        total_symbols = len(symbols)
        
        # Initialize progress tracker
        title = f"Fetching Data for {total_symbols} Stocks"
        tracker = StreamingProgressTracker(total_symbols, title)
        
        # Process in batches
        batch_size = 50
        total_batches = (total_symbols + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            batch_start = batch_num * batch_size
            batch_end = min(batch_start + batch_size, total_symbols)
            batch_symbols = symbols[batch_start:batch_end]
            
            # Start batch
            tracker.start_batch(
                batch_num + 1, 
                total_batches, 
                f"Symbols {batch_start + 1}-{batch_end}"
            )
            
            try:
                # Fetch data for this batch
                stock_data = analyzer.fetcher.fetch_multiple_stocks(batch_symbols, period="3mo")
                
                # Process each stock in the batch
                for symbol in batch_symbols:
                    if symbol in stock_data and stock_data[symbol] is not None:
                        data = stock_data[symbol]
                        
                        # Store price data
                        success = analyzer.data_manager.insert_price_data(data)
                        
                        if success:
                            # Store indicators data
                            indicators_data = data[['symbol', 'date', 'sma_20']].copy()
                            analyzer.data_manager.insert_indicators_data(indicators_data)
                        
                        tracker.increment(success=success, status=f"Processed {symbol}")
                    else:
                        tracker.increment(success=False, status=f"Failed {symbol}")
                    
                    # Small delay to show progress
                    time.sleep(0.01)
                
            except Exception as e:
                # Handle batch failure
                for symbol in batch_symbols:
                    tracker.increment(success=False, status=f"Batch error: {symbol}")
        
        # Complete processing
        tracker.complete()
        
        # Update session state
        st.session_state.data_fetched = True
        from datetime import datetime
        st.session_state.last_fetch_time = datetime.now()
        
        # Clear caches
        st.cache_data.clear()
        
        # Cleanup UI
        tracker.cleanup()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error during streaming fetch: {str(e)}")
        return False
