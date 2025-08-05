"""
Streamlit Stock Technical Analysis Dashboard
A modern web-based interface for stock analysis and screening.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import our modules
from technical_analysis import TechnicalAnalyzer
from stock_data_fetcher import StockDataFetcher
from stock_data_manager import StockDataManager

# Page configuration
st.set_page_config(
    page_title="Stock Technical Analysis Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = TechnicalAnalyzer(verbose=False)
if 'data_fetched' not in st.session_state:
    st.session_state.data_fetched = False
if 'last_fetch_time' not in st.session_state:
    st.session_state.last_fetch_time = None

def main():
    """Main dashboard function."""
    
    # Header
    st.markdown('<h1 class="main-header">📈 Stock Technical Analysis Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Dashboard Controls")
        
        # Data fetch section
        st.subheader("📊 Data Management")
        
        if st.button("🔄 Fetch Latest Data", type="primary", use_container_width=True):
            use_popular_only = (fetch_mode == "Popular Stocks Only")
            max_stocks_param = max_stocks if max_stocks > 0 else None
            fetch_stock_data(use_popular_only, max_stocks_param)
        
        if st.session_state.last_fetch_time:
            st.success(f"Last updated: {st.session_state.last_fetch_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Navigation
        st.subheader("🧭 Navigation")
        page = st.selectbox(
            "Select Analysis View",
            ["📊 Dashboard Overview", "📈 Stocks Above SMA", "🚀 Breakout Patterns", "📋 Data Explorer"]
        )
        
        # Settings
        st.subheader("⚙️ Settings")
        sma_period = st.selectbox("SMA Period", [20, 50], index=0)

        # Data fetch options
        st.subheader("📊 Data Options")
        fetch_mode = st.radio(
            "Fetch Mode",
            ["All NSE Stocks", "Popular Stocks Only"],
            index=0,
            help="All NSE Stocks: Fetch data for all stocks in database\nPopular Stocks: Only fetch reliable stocks"
        )

        if fetch_mode == "All NSE Stocks":
            max_stocks = st.number_input(
                "Max Stocks (0 = All)",
                min_value=0,
                max_value=5000,
                value=0,
                step=50,
                help="Limit number of stocks to fetch (0 = fetch all stocks)"
            )
        else:
            max_stocks = 50

        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    # Auto-refresh logic
    if auto_refresh and st.session_state.data_fetched:
        time.sleep(30)
        st.rerun()
    
    # Main content based on selected page
    if page == "📊 Dashboard Overview":
        show_dashboard_overview(sma_period)
    elif page == "📈 Stocks Above SMA":
        show_stocks_above_sma(sma_period)
    elif page == "🚀 Breakout Patterns":
        show_breakout_patterns()
    elif page == "📋 Data Explorer":
        show_data_explorer()

def fetch_stock_data(use_popular_only=False, max_stocks=None):
    """Fetch latest stock data with progress indication."""

    with st.spinner("🔄 Setting up database schema..."):
        if not st.session_state.analyzer.setup_database():
            st.error("❌ Failed to setup database schema")
            return

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        if use_popular_only:
            status_text.text("📡 Fetching popular stock data...")
        else:
            if max_stocks:
                status_text.text(f"📡 Fetching data for up to {max_stocks} stocks...")
            else:
                status_text.text("📡 Fetching data for ALL NSE stocks...")

        progress_bar.progress(25)

        # Fetch data with new parameters
        if st.session_state.analyzer.fetch_and_store_data(
            use_popular_only=use_popular_only,
            max_stocks=max_stocks
        ):
            progress_bar.progress(75)
            status_text.text("💾 Storing data in database...")

            progress_bar.progress(100)
            status_text.text("✅ Data fetch completed!")

            st.session_state.data_fetched = True
            st.session_state.last_fetch_time = datetime.now()

            time.sleep(1)
            status_text.empty()
            progress_bar.empty()

            # Show success message with details
            stats = st.session_state.analyzer.get_summary_statistics()
            total_stocks = stats.get('total_stocks_with_data', 0)
            st.success(f"🎉 Successfully fetched and stored data for {total_stocks} stocks!")
            st.rerun()

        else:
            st.error("❌ Failed to fetch stock data")

    except Exception as e:
        st.error(f"❌ Error during data fetch: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

def show_dashboard_overview(sma_period):
    """Show main dashboard overview."""
    
    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return
    
    # Get summary statistics
    stats = st.session_state.analyzer.get_summary_statistics()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Stocks",
            value=stats.get('total_stocks_with_data', 0),
            help="Total number of stocks with available data"
        )
    
    with col2:
        st.metric(
            label=f"📈 Above {sma_period}-Day SMA",
            value=stats.get('stocks_above_20_sma', 0),
            help=f"Stocks currently trading above their {sma_period}-day Simple Moving Average"
        )
    
    with col3:
        st.metric(
            label="🚀 Breakout Patterns",
            value=stats.get('open_high_patterns', 0),
            help="Stocks showing open=high breakout patterns"
        )
    
    with col4:
        total = stats.get('total_stocks_with_data', 1)
        momentum_pct = (stats.get('stocks_above_20_sma', 0) / total) * 100
        st.metric(
            label="💪 Momentum %",
            value=f"{momentum_pct:.1f}%",
            help="Percentage of stocks showing upward momentum"
        )
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        show_sma_distribution_chart(sma_period)
    
    with col2:
        show_top_performers_chart(sma_period)

def show_sma_distribution_chart(sma_period):
    """Show distribution of stocks above/below SMA."""
    
    stats = st.session_state.analyzer.get_summary_statistics()
    above_sma = stats.get('stocks_above_20_sma', 0)
    total = stats.get('total_stocks_with_data', 1)
    below_sma = total - above_sma
    
    fig = px.pie(
        values=[above_sma, below_sma],
        names=[f'Above {sma_period}-Day SMA', f'Below {sma_period}-Day SMA'],
        title=f"Stock Distribution: {sma_period}-Day SMA",
        color_discrete_sequence=['#2ecc71', '#e74c3c']
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)

def show_top_performers_chart(sma_period):
    """Show top performing stocks above SMA."""
    
    stocks_above_sma = st.session_state.analyzer.get_stocks_above_sma(sma_period)
    
    if stocks_above_sma is not None and not stocks_above_sma.empty:
        # Get top 10 performers
        top_stocks = stocks_above_sma.head(10)
        
        fig = px.bar(
            top_stocks,
            x='percentage_above_sma',
            y='symbol',
            orientation='h',
            title=f"Top 10 Stocks Above {sma_period}-Day SMA",
            labels={'percentage_above_sma': '% Above SMA', 'symbol': 'Stock Symbol'},
            color='percentage_above_sma',
            color_continuous_scale='viridis'
        )
        
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No stocks currently above {sma_period}-day SMA")

def show_stocks_above_sma(sma_period):
    """Show detailed view of stocks above SMA."""

    st.header(f"📈 Stocks Above {sma_period}-Day SMA")

    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return

    stocks_above_sma = st.session_state.analyzer.get_stocks_above_sma(sma_period)

    if stocks_above_sma is None or stocks_above_sma.empty:
        st.info(f"No stocks currently trading above their {sma_period}-day SMA.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Stocks", len(stocks_above_sma))
    with col2:
        avg_percentage = stocks_above_sma['percentage_above_sma'].mean()
        st.metric("Average % Above SMA", f"{avg_percentage:.2f}%")
    with col3:
        max_percentage = stocks_above_sma['percentage_above_sma'].max()
        st.metric("Highest % Above SMA", f"{max_percentage:.2f}%")

    # Interactive table
    st.subheader("📋 Detailed Stock List")

    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        min_percentage = st.slider("Minimum % Above SMA", 0.0, 20.0, 0.0, 0.5)
    with col2:
        max_results = st.selectbox("Max Results", [10, 25, 50, 100], index=1)

    # Filter data
    filtered_stocks = stocks_above_sma[
        stocks_above_sma['percentage_above_sma'] >= min_percentage
    ].head(max_results)

    # Format the dataframe for display
    display_df = filtered_stocks.copy()
    display_df['close'] = display_df['close'].round(2)
    display_df[f'sma_{sma_period}'] = display_df[f'sma_{sma_period}'].round(2)
    display_df['percentage_above_sma'] = display_df['percentage_above_sma'].round(2)

    # Rename columns for better display
    column_mapping = {
        'symbol': 'Symbol',
        'close': 'Current Price',
        f'sma_{sma_period}': f'{sma_period}-Day SMA',
        'percentage_above_sma': '% Above SMA',
        'date': 'Date'
    }
    display_df = display_df.rename(columns=column_mapping)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% Above SMA": st.column_config.ProgressColumn(
                "% Above SMA",
                help="Percentage above SMA",
                min_value=0,
                max_value=20,
                format="%.2f%%"
            )
        }
    )

    # Export functionality
    if st.button("📥 Export to CSV"):
        csv = filtered_stocks.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"stocks_above_{sma_period}_sma_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def show_breakout_patterns():
    """Show stocks with open=high breakout patterns."""

    st.header("🚀 Open = High Breakout Patterns")

    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return

    patterns = st.session_state.analyzer.get_open_high_patterns()

    if patterns is None or patterns.empty:
        st.info("No open=high breakout patterns found in current data.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Patterns", len(patterns))
    with col2:
        avg_breakout = patterns['breakout_percentage'].mean()
        st.metric("Average Breakout %", f"{avg_breakout:.2f}%")
    with col3:
        max_breakout = patterns['breakout_percentage'].max()
        st.metric("Highest Breakout %", f"{max_breakout:.2f}%")

    # Interactive chart
    st.subheader("📊 Breakout Performance")

    fig = px.scatter(
        patterns,
        x='symbol',
        y='breakout_percentage',
        size='breakout_percentage',
        color='breakout_percentage',
        title="Breakout Patterns by Stock",
        labels={'breakout_percentage': 'Breakout %', 'symbol': 'Stock Symbol'},
        color_continuous_scale='viridis'
    )

    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.subheader("📋 Pattern Details")

    # Format the dataframe
    display_df = patterns.copy()
    numeric_columns = ['yesterday_open', 'yesterday_high', 'today_close', 'breakout_percentage']
    for col in numeric_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(2)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Export functionality
    if st.button("📥 Export Patterns to CSV"):
        csv = patterns.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"breakout_patterns_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def show_data_explorer():
    """Show raw data exploration interface."""

    st.header("📋 Data Explorer")

    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return

    # Get latest prices
    latest_prices = st.session_state.analyzer.data_manager.get_latest_prices(limit=1000)

    if latest_prices is None or latest_prices.empty:
        st.error("No price data available.")
        return

    # Data overview
    st.subheader("📊 Data Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(latest_prices))
    with col2:
        st.metric("Unique Stocks", latest_prices['symbol'].nunique())
    with col3:
        date_range = latest_prices['date'].nunique()
        st.metric("Date Range (days)", date_range)
    with col4:
        avg_volume = latest_prices['volume'].mean()
        st.metric("Avg Volume", f"{avg_volume:,.0f}")

    # Stock selector
    st.subheader("🔍 Stock Data Viewer")

    selected_stocks = st.multiselect(
        "Select stocks to view",
        options=sorted(latest_prices['symbol'].unique()),
        default=sorted(latest_prices['symbol'].unique())[:5],
        max_selections=10
    )

    if selected_stocks:
        # Filter data
        filtered_data = latest_prices[latest_prices['symbol'].isin(selected_stocks)]

        # Show price chart
        fig = px.line(
            filtered_data,
            x='date',
            y='close',
            color='symbol',
            title="Stock Price Trends",
            labels={'close': 'Close Price', 'date': 'Date'}
        )

        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Show raw data
        st.subheader("📋 Raw Data")
        st.dataframe(
            filtered_data.sort_values(['symbol', 'date']),
            use_container_width=True,
            hide_index=True
        )

if __name__ == "__main__":
    main()
