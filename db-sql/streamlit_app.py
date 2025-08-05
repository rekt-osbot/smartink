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
import os

# Import our modules
from technical_analysis import TechnicalAnalyzer
from stock_data_fetcher import StockDataFetcher
from stock_data_manager import StockDataManager
from streamlit_streaming import stream_stock_data_fetch

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
if 'cloud_warning_shown' not in st.session_state:
    st.session_state.cloud_warning_shown = False

# Check if running on Streamlit Cloud
def is_streamlit_cloud():
    """Check if running on Streamlit Cloud."""
    return bool(os.getenv('STREAMLIT_SHARING_MODE') or os.getenv('STREAMLIT_CLOUD'))

# Show cloud storage warning
def show_cloud_warning():
    """Show warning about data persistence on Streamlit Cloud."""
    if is_streamlit_cloud() and not st.session_state.cloud_warning_shown:
        st.warning("""
        ⚠️ **Running on Streamlit Cloud**: Data is stored temporarily and will be lost when the app restarts.
        For persistent data, please run the app locally or fetch data fresh each session.
        """)
        st.session_state.cloud_warning_shown = True

def check_data_availability():
    """Check if data is available and update session state accordingly."""
    try:
        stats = st.session_state.analyzer.get_summary_statistics()
        if stats and stats.get('total_stocks_with_data', 0) > 0:
            st.session_state.data_fetched = True
            return True
        else:
            st.session_state.data_fetched = False
            return False
    except Exception:
        st.session_state.data_fetched = False
        return False

# Cached functions to avoid repeated database queries
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_summary_statistics(_analyzer):
    """Get summary statistics with caching."""
    return _analyzer.get_summary_statistics()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_stocks_above_sma(_analyzer, sma_period, max_distance=None):
    """Get stocks above SMA with caching."""
    return _analyzer.get_stocks_above_sma(sma_period, max_distance)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_stocks_near_sma_breakout(_analyzer, sma_period, max_distance=5.0):
    """Get stocks near SMA breakout with caching."""
    return _analyzer.get_stocks_near_sma_breakout(sma_period, max_distance)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_breakout_patterns(_analyzer):
    """Get breakout patterns with caching."""
    return _analyzer.get_open_high_patterns()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_latest_prices(_analyzer, limit=1000):
    """Get latest prices with caching."""
    return _analyzer.data_manager.get_latest_prices(limit=limit)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_master_stock_count(_analyzer):
    """Get count of stocks in master list with caching."""
    try:
        symbols = _analyzer.fetcher.get_stocks_from_database()
        return len(symbols) if symbols else 0
    except Exception:
        return 0

def main():
    """Main dashboard function."""

    # Page configuration
    st.set_page_config(
        page_title="SmartInk - Stock Analysis",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header
    st.markdown('<h1 class="main-header">📈 SmartInk - Intelligent Stock Analysis</h1>', unsafe_allow_html=True)
    st.markdown("*Professional-grade stock analysis focusing on actionable trading opportunities*")

    # Show cloud warning if applicable
    show_cloud_warning()

    # Check data availability on startup
    if not st.session_state.data_fetched:
        check_data_availability()
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Dashboard Controls")

        # Price Data Section (Frequent Updates)
        st.subheader("📊 Price Data (Frequent)")
        st.info("Fetch daily prices for analysis.")

        fetch_mode = st.radio(
            "Select stock universe",
            ["Popular Stocks Only", "All Stocks in DB"],
            index=0,
            key='fetch_mode',
            help="Popular Stocks: Curated list. All Stocks: Use all symbols currently in the master list."
        )

        if fetch_mode == "All Stocks in DB":
            max_stocks = st.number_input(
                "Max Stocks to Fetch (0 = All)",
                min_value=0,
                max_value=5000,
                value=50,  # Default to 50 to prevent accidental large fetches
                step=50,
                help="Limit number of stocks to fetch price data for (0 = fetch all)."
            )
        else:
            max_stocks = 50  # Popular stocks are a fixed list

        if st.button("🔄 Fetch Latest Price Data", type="primary", use_container_width=True):
            use_popular_only = (fetch_mode == "Popular Stocks Only")
            max_stocks_param = max_stocks if max_stocks > 0 else None

            # Clear any existing cache first
            st.cache_data.clear()

            # Show cloud-specific message
            if is_streamlit_cloud():
                st.info("🌐 Fetching fresh price data for this session...")

            # Use streaming fetch for better UX
            with st.spinner("🔄 Setting up database schema..."):
                if not st.session_state.analyzer.setup_database():
                    st.error("❌ Failed to setup database schema")
                else:
                    # Stream the data fetching process
                    if stream_stock_data_fetch(st.session_state.analyzer, use_popular_only, max_stocks_param):
                        # Force refresh of data availability check
                        check_data_availability()
                        st.success("✅ Price data fetched successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Price data fetch failed")

        if st.session_state.last_fetch_time:
            st.success(f"Prices last updated: {st.session_state.last_fetch_time.strftime('%H:%M:%S')}")

        st.divider()

        # Master Stock List Section (Infrequent Updates)
        st.subheader("📦 Master Stock List (Infrequent)")
        st.info("Update the entire list of tradable stocks from NSE.")

        if st.button("🌍 Update Master Stock List from NSE", use_container_width=True):
            with st.spinner("Fetching latest stock list from NSE and rebuilding database... This may take a moment."):
                if st.session_state.analyzer.refresh_master_stock_list():
                    st.success("✅ Master stock list updated successfully!")
                    st.info("The new stock list is now available for price fetching.")
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Failed to update the master stock list.")

        st.caption("Run this periodically (e.g., monthly) to include new stocks or remove delisted ones.")

        st.divider()

        # Navigation
        st.subheader("🧭 Navigation")
        page = st.selectbox(
            "Select Analysis View",
            ["📊 Dashboard Overview", "🎯 SMA Breakout Opportunities", "📈 Stocks Above SMA", "🚀 Open=High Patterns", "📋 Data Explorer"]
        )

        # Settings
        st.subheader("⚙️ Settings")
        sma_period = st.selectbox("SMA Period", [20, 50], index=0)
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    # Auto-refresh logic
    if auto_refresh and st.session_state.data_fetched:
        time.sleep(30)
        st.rerun()
    
    # Main content based on selected page
    if page == "📊 Dashboard Overview":
        show_dashboard_overview(sma_period)
    elif page == "🎯 SMA Breakout Opportunities":
        show_sma_breakout_opportunities(sma_period)
    elif page == "📈 Stocks Above SMA":
        show_stocks_above_sma(sma_period)
    elif page == "🚀 Open=High Patterns":
        show_breakout_patterns()
    elif page == "📋 Data Explorer":
        show_data_explorer()

# Removed old fetch function - now using streaming version

def show_dashboard_overview(sma_period):
    """Show main dashboard overview."""

    st.header("📊 Stock Market Dashboard")

    if not st.session_state.data_fetched:
        if is_streamlit_cloud():
            st.warning("""
            ⚠️ **No price data available** - This is expected on first visit to Streamlit Cloud.

            **To get started:**
            1. **First time users**: Click "🌍 Update Master Stock List from NSE" to get the full stock universe
            2. **Then**: Click "🔄 Fetch Latest Price Data" to get current prices
            3. **Quick start**: Just use "Popular Stocks Only" (skips step 1)

            💡 **Note**: Data is temporary on Streamlit Cloud and will need to be refetched each session.
            """)
        else:
            st.warning("⚠️ No price data available. Please fetch stock data first using the sidebar.")
        return

    try:
        # Get summary statistics (cached)
        stats = get_cached_summary_statistics(st.session_state.analyzer)

        if not stats or stats.get('total_stocks_with_data', 0) == 0:
            st.warning("⚠️ No stock data found. Please fetch data first.")
            return
    except Exception as e:
        st.error(f"❌ Error loading dashboard data: {str(e)}")
        return
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        master_count = get_cached_master_stock_count(st.session_state.analyzer)
        st.metric(
            label="📦 Master List",
            value=master_count,
            help="Total stocks in NSE master list"
        )

    with col2:
        st.metric(
            label="📊 With Price Data",
            value=stats.get('total_stocks_with_data', 0),
            help="Stocks with current price data"
        )
    
    with col3:
        # Get actionable breakout opportunities
        try:
            breakout_opportunities = get_cached_stocks_near_sma_breakout(st.session_state.analyzer, sma_period, 5.0)
            breakout_count = len(breakout_opportunities) if breakout_opportunities is not None else 0
        except Exception:
            breakout_count = 0

        st.metric(
            label=f"🎯 Breakout Opps",
            value=breakout_count,
            help=f"Stocks within ±5% of {sma_period}-day SMA (actionable opportunities)"
        )

    with col4:
        st.metric(
            label="🚀 Breakout Patterns",
            value=stats.get('open_high_patterns', 0),
            help="Stocks showing open=high breakout patterns"
        )

    with col5:
        total = stats.get('total_stocks_with_data', 0)
        if total > 0:
            momentum_pct = (stats.get('stocks_above_20_sma', 0) / total) * 100
            st.metric(
                label="💪 Momentum %",
                value=f"{momentum_pct:.1f}%",
                help="Percentage of stocks showing upward momentum"
            )
        else:
            st.metric(
                label="💪 Momentum %",
                value="0.0%",
                help="No data available - fetch stock data first"
            )
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        show_sma_distribution_chart(sma_period)
    
    with col2:
        show_top_performers_chart(sma_period)

def show_sma_distribution_chart(sma_period):
    """Show distribution of actionable vs extended stocks."""

    # Get total stocks first
    stats = get_cached_summary_statistics(st.session_state.analyzer)
    total = stats.get('total_stocks_with_data', 0)

    if total == 0:
        st.info("No data available. Please fetch stock data first.")
        return

    # Get actionable opportunities (within ±5% of SMA)
    breakout_opportunities = get_cached_stocks_near_sma_breakout(st.session_state.analyzer, sma_period, 5.0)
    actionable_count = len(breakout_opportunities) if breakout_opportunities is not None else 0

    # Get extended stocks (>5% above SMA)
    extended_stocks = get_cached_stocks_above_sma(st.session_state.analyzer, sma_period)
    if extended_stocks is not None:
        extended_count = len(extended_stocks[extended_stocks['percentage_above_sma'] > 5.0])
    else:
        extended_count = 0

    # Calculate other count (ensure non-negative)
    other_count = max(0, total - actionable_count - extended_count)

    # Only create chart if we have data
    if actionable_count + extended_count + other_count > 0:
        # Create pie chart with trading-focused categories
        fig = px.pie(
            values=[actionable_count, extended_count, other_count],
            names=[f'🎯 Actionable (±5% of SMA)', f'📈 Extended (>5% above SMA)', f'📉 Other/Below SMA'],
            title=f"Trading Opportunities: {sma_period}-Day SMA",
            color_discrete_map={
                f'🎯 Actionable (±5% of SMA)': '#f39c12',    # Orange for actionable
                f'📈 Extended (>5% above SMA)': '#2ecc71',    # Green for extended
                f'📉 Other/Below SMA': '#e74c3c'             # Red for below/other
            }
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No stock data available for chart.")

def show_top_performers_chart(sma_period):
    """Show actionable breakout opportunities."""

    try:
        breakout_opportunities = get_cached_stocks_near_sma_breakout(st.session_state.analyzer, sma_period, 5.0)
    except Exception:
        breakout_opportunities = None

    if breakout_opportunities is not None and not breakout_opportunities.empty:
        # Get top 10 opportunities (closest to SMA or fresh breakouts)
        top_opportunities = breakout_opportunities.head(10)

        # Color code by breakout status
        color_map = {
            'Fresh Breakout Above': '#2ecc71',
            'Fresh Breakdown Below': '#e74c3c',
            'Holding Above': '#f39c12',
            'Holding Below': '#ff6b6b',
            'At SMA': '#95a5a6'
        }

        colors = [color_map.get(status, '#95a5a6') for status in top_opportunities['breakout_status']]

        fig = px.bar(
            top_opportunities,
            x='percentage_from_sma',
            y='symbol',
            orientation='h',
            title=f"Top 10 SMA Breakout Opportunities",
            labels={'percentage_from_sma': '% From SMA', 'symbol': 'Stock Symbol'},
            color='breakout_status',
            color_discrete_map=color_map
        )

        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No actionable opportunities near {sma_period}-day SMA")

def show_sma_breakout_opportunities(sma_period):
    """Show stocks near SMA breakout - actionable trading opportunities."""

    st.header(f"🎯 SMA Breakout Opportunities ({sma_period}-Day)")

    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return

    # Add controls for breakout analysis
    col1, col2 = st.columns(2)
    with col1:
        max_distance = st.slider(
            "Max Distance from SMA (%)",
            1.0, 10.0, 5.0, 0.5,
            help="Stocks within this percentage of the SMA (±)"
        )
    with col2:
        breakout_filter = st.selectbox(
            "Filter by Status",
            ["All", "Fresh Breakouts Only", "Fresh Breakdowns Only", "Holding Above", "Holding Below"]
        )

    # Get breakout opportunities
    breakout_stocks = get_cached_stocks_near_sma_breakout(st.session_state.analyzer, sma_period, max_distance)

    if breakout_stocks is None or breakout_stocks.empty:
        st.info(f"No stocks found within ±{max_distance}% of their {sma_period}-day SMA.")
        return

    # Apply breakout filter
    if breakout_filter != "All":
        if breakout_filter == "Fresh Breakouts Only":
            breakout_stocks = breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakout Above']
        elif breakout_filter == "Fresh Breakdowns Only":
            breakout_stocks = breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakdown Below']
        elif breakout_filter == "Holding Above":
            breakout_stocks = breakout_stocks[breakout_stocks['breakout_status'] == 'Holding Above']
        elif breakout_filter == "Holding Below":
            breakout_stocks = breakout_stocks[breakout_stocks['breakout_status'] == 'Holding Below']

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Opportunities", len(breakout_stocks))
    with col2:
        fresh_breakouts = len(breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakout Above'])
        st.metric("🟢 Fresh Breakouts", fresh_breakouts)
    with col3:
        fresh_breakdowns = len(breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakdown Below'])
        st.metric("🔴 Fresh Breakdowns", fresh_breakdowns)
    with col4:
        avg_distance = breakout_stocks['percentage_from_sma'].abs().mean()
        st.metric("Avg Distance from SMA", f"{avg_distance:.1f}%")

    # Breakout status distribution
    st.subheader("📊 Breakout Status Distribution")
    status_counts = breakout_stocks['breakout_status'].value_counts()

    fig = px.bar(
        x=status_counts.index,
        y=status_counts.values,
        title="Distribution of Breakout Opportunities",
        labels={'x': 'Breakout Status', 'y': 'Number of Stocks'},
        color=status_counts.values,
        color_continuous_scale='viridis'
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Interactive table
    st.subheader("🎯 Actionable Opportunities")

    # Format the dataframe for display
    display_df = breakout_stocks.copy()
    display_df['close'] = display_df['close'].round(2)
    display_df[f'sma_{sma_period}'] = display_df[f'sma_{sma_period}'].round(2)
    display_df['percentage_from_sma'] = display_df['percentage_from_sma'].round(2)

    # Add status emoji
    status_emoji_map = {
        'Fresh Breakout Above': '🟢',
        'Fresh Breakdown Below': '🔴',
        'Holding Above': '🟡',
        'Holding Below': '🟠',
        'At SMA': '⚪'
    }
    display_df['status_display'] = display_df['breakout_status'].map(
        lambda x: f"{status_emoji_map.get(x, '⚪')} {x}"
    )

    # Rename columns for better display
    column_mapping = {
        'symbol': 'Symbol',
        'close': 'Current Price',
        f'sma_{sma_period}': f'{sma_period}-Day SMA',
        'percentage_from_sma': '% From SMA',
        'status_display': 'Breakout Status',
        'volume': 'Volume',
        'date': 'Date'
    }
    display_df = display_df.rename(columns=column_mapping)

    # Select columns to display
    display_columns = ['Symbol', 'Current Price', f'{sma_period}-Day SMA', '% From SMA', 'Breakout Status', 'Volume', 'Date']

    st.dataframe(
        display_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "% From SMA": st.column_config.NumberColumn(
                "% From SMA",
                help="Percentage distance from SMA (+ above, - below)",
                format="%.2f%%"
            ),
            "Volume": st.column_config.NumberColumn(
                "Volume",
                help="Trading volume",
                format="%d"
            )
        }
    )

    # Export functionality
    if st.button("📥 Export Opportunities to CSV"):
        csv = breakout_stocks.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"sma_breakout_opportunities_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # Trading insights
    st.subheader("💡 Trading Insights")

    fresh_breakouts_count = len(breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakout Above'])
    fresh_breakdowns_count = len(breakout_stocks[breakout_stocks['breakout_status'] == 'Fresh Breakdown Below'])

    if fresh_breakouts_count > 0:
        st.success(f"🟢 **{fresh_breakouts_count} Fresh Breakouts** - Stocks breaking above {sma_period}-day SMA today. Consider for long positions.")

    if fresh_breakdowns_count > 0:
        st.error(f"🔴 **{fresh_breakdowns_count} Fresh Breakdowns** - Stocks breaking below {sma_period}-day SMA today. Consider for short positions or avoid.")

    holding_above = len(breakout_stocks[breakout_stocks['breakout_status'] == 'Holding Above'])
    if holding_above > 0:
        st.info(f"🟡 **{holding_above} Holding Above** - Stocks maintaining above {sma_period}-day SMA. Monitor for continuation.")

def show_stocks_above_sma(sma_period):
    """Show detailed view of stocks above SMA."""

    st.header(f"📈 Stocks Above {sma_period}-Day SMA")

    if not st.session_state.data_fetched:
        st.warning("⚠️ No data available. Please fetch stock data first using the sidebar.")
        return

    # Add filter for maximum distance
    col1, col2 = st.columns(2)
    with col1:
        max_distance = st.slider("Max % Above SMA", 0.0, 20.0, 10.0, 0.5)
    with col2:
        max_results = st.selectbox("Max Results", [10, 25, 50, 100], index=1)

    stocks_above_sma = get_cached_stocks_above_sma(st.session_state.analyzer, sma_period, max_distance)

    if stocks_above_sma is None or stocks_above_sma.empty:
        st.info(f"No stocks currently trading above their {sma_period}-day SMA within {max_distance}%.")
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

    # Filter data
    filtered_stocks = stocks_above_sma.head(max_results)

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
                max_value=max_distance,
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

    patterns = get_cached_breakout_patterns(st.session_state.analyzer)

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

    # Get latest prices (cached)
    latest_prices = get_cached_latest_prices(st.session_state.analyzer, limit=1000)

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
