# 📈 SmartInk - Intelligent Stock Analysis Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://smartink.streamlit.app/)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-live-brightgreen.svg)

**🚀 Live Demo**: [https://smartink.streamlit.app/](https://smartink.streamlit.app/)

SmartInk is a professional-grade stock analysis platform that focuses on **actionable trading opportunities** rather than showing you stocks that are already too late to enter. Built for day traders and swing traders who need to identify fresh breakouts and setups near key technical levels.

## 🎯 **Key Features**

### **🎯 SMA Breakout Opportunities**
- **Fresh Breakouts**: Stocks breaking above/below 20-day SMA TODAY
- **Actionable Range**: Focus on stocks within ±5% of SMA (not extended moves)
- **Real-time Status**: Track breakout status with color-coded indicators
- **Trading Signals**: Clear BUY/SELL signals based on SMA breakouts

### **📊 Professional Dashboard**
- **Live Metrics**: Total stocks, breakout opportunities, momentum percentage
- **Smart Visualizations**: Trading-focused pie charts and bar graphs
- **Performance Tracking**: Success rates and processing statistics
- **Interactive Filters**: Customize analysis parameters

### **🚀 Advanced Pattern Recognition**
- **Open=High Patterns**: Identify potential breakout setups
- **Volume Analysis**: Track trading volume alongside price action
- **Multi-timeframe**: Support for different SMA periods (20, 50-day)

### **⚡ High-Performance Architecture**
- **Bulk Data Fetching**: 60% faster than individual API calls
- **Smart Caching**: 5-minute TTL for instant UI responses
- **Memory Efficient**: Batch processing for thousands of stocks
- **Streaming Progress**: Real-time updates during data fetching

## 🎯 **Trading Philosophy**

### **SmartInk vs Traditional Stock Screeners**

| Feature | Traditional Screeners | SmartInk |
|---------|----------------------|----------|
| **Focus** | All stocks above SMA | Actionable opportunities only |
| **Entry Timing** | Often too late (8-10% extended) | Early identification (±5% of SMA) |
| **Risk Management** | Shows extended moves | Filters out high-risk entries |
| **Signal Quality** | Mixed signals | Fresh breakouts prioritized |
| **Trading Edge** | Reactive | Proactive |

### **❌ What We DON'T Show (Avoid These)**
- Stocks already 8-10% above SMA (too late to enter)
- Extended momentum plays (high risk)
- Chasing moves that already happened

### **✅ What We DO Show (Actionable Opportunities)**
- **Fresh Breakouts**: Stocks breaking above SMA today (BUY signals)
- **Near SMA Setups**: Stocks within ±5% of SMA (watch for breakouts)
- **Early Identification**: Catch moves before they become extended
- **Lower Risk Entries**: Better risk/reward ratios

## 🚀 **Quick Start**

1. **Visit the App**: [https://smartink.streamlit.app/](https://smartink.streamlit.app/)

2. **Fetch Data**: Click "🔄 Fetch Latest Data" in the sidebar
   - Choose "Popular Stocks Only" for quick start
   - Or "All NSE Stocks" for comprehensive analysis

3. **Analyze Opportunities**: Navigate to "🎯 SMA Breakout Opportunities"
   - View fresh breakouts (immediate action signals)
   - Monitor stocks near SMA (setup opportunities)
   - Avoid extended stocks (risk management)

4. **Export Results**: Download CSV files for further analysis

## 📊 **Dashboard Pages**

### **📊 Dashboard Overview**
- Key metrics and market momentum
- Trading opportunities distribution
- Top actionable breakouts

### **🎯 SMA Breakout Opportunities** ⭐ **MAIN TRADING PAGE**
- **🟢 Fresh Breakout Above**: BUY signals
- **🔴 Fresh Breakdown Below**: SELL signals  
- **🟡 Holding Above**: Monitor for continuation
- **🟠 Holding Below**: Watch for potential bounce
- **⚪ At SMA**: Setup opportunities

### **📈 Stocks Above SMA**
- Traditional above-SMA analysis
- Filter by maximum distance from SMA
- Avoid extended moves

### **🚀 Open=High Patterns**
- Breakout pattern recognition
- Volume confirmation signals

### **📋 Data Explorer**
- Raw data access and exploration
- Export functionality

## 🛠️ **Technical Stack**

- **Frontend**: Streamlit (Interactive web interface)
- **Data Source**: yfinance (Yahoo Finance API)
- **Database**: SQLite (Local data storage)
- **Analytics**: Pandas, NumPy (Data processing)
- **Visualization**: Plotly (Interactive charts)
- **Deployment**: Streamlit Cloud

## 📈 **Performance Optimizations**

### **Network Efficiency**
- **Bulk Downloads**: Fetch multiple stocks in single API calls
- **Smart Batching**: Process 100 stocks per batch
- **Rate Limiting**: Optimized delays to prevent API throttling

### **Memory Management**
- **Batch Processing**: Constant memory usage regardless of stock count
- **Garbage Collection**: Explicit cleanup between batches
- **Streaming Updates**: Real-time progress without memory leaks

### **Database Performance**
- **Upsert Logic**: Proper INSERT OR REPLACE for duplicate handling
- **Bulk Operations**: 10x faster than individual inserts
- **Indexed Queries**: Optimized for fast retrieval

### **UI Responsiveness**
- **Smart Caching**: 5-minute TTL for database queries
- **Instant Responses**: After initial data load
- **Auto-refresh**: Cache clearing on new data

## 🎯 **Trading Use Cases**

### **Day Trading**
```
🟢 RELIANCE: +2.1% from SMA - Fresh Breakout Above
→ Stock broke above 20-day SMA today - CONSIDER LONG POSITION
```

### **Swing Trading Setup**
```
⚪ TCS: -1.2% from SMA - Holding Below  
→ Stock near SMA support - WATCH FOR BREAKOUT
```

### **Risk Management**
```
❌ INFY: +8.5% above SMA - Extended
→ Already too far from SMA - WAIT FOR PULLBACK
```

## 📊 **Data Coverage**

- **Market**: NSE (National Stock Exchange of India)
- **Universe**: 2,138+ stocks
- **Timeframe**: 3-month historical data
- **Indicators**: 20-day and 50-day Simple Moving Averages
- **Update Frequency**: On-demand (manual refresh)

## 🔧 **Local Development**

```bash
# Clone the repository
git clone <repository-url>
cd smartink

# Install dependencies (using uv for faster installs)
uv pip install -r requirements.txt

# Or with regular pip
pip install -r requirements.txt
```

### **Two Official Entry Points:**

#### **1. Interactive Web UI (Primary)**
```bash
# Run the Streamlit web application
uv run streamlit run db-sql/streamlit_app.py
```

#### **2. CLI Automation (Administrative)**
```bash
# System check
python db-sql/main.py --system-check

# Refresh master stock list from NSE
python db-sql/main.py --refresh-database

# Fetch prices for popular stocks
python db-sql/main.py --fetch-prices --popular-only

# Fetch prices for up to 100 stocks
python db-sql/main.py --fetch-prices --limit 100

# Clean up old data
python db-sql/main.py --cleanup-data

# Verbose output
python db-sql/main.py --system-check --verbose
```

### **Testing**
```bash
# Run tests
uv run python db-sql/test_optimizations.py
uv run python db-sql/test_actionable_opportunities.py
```

## 🧪 **Testing**

The project includes comprehensive test suites:

- **Performance Tests**: `test_optimizations.py` - Validates all optimizations
- **Trading Logic Tests**: `test_actionable_opportunities.py` - Tests breakout detection
- **Streaming Tests**: `test_streaming.py` - Validates real-time progress updates

## 📁 **Project Structure**

```
smartink/
├── db-sql/                          # Main application directory
│   ├── streamlit_app.py            # Main Streamlit application
│   ├── technical_analysis.py       # Core analysis engine
│   ├── stock_data_fetcher.py       # Data fetching with bulk optimization
│   ├── stock_data_manager.py       # Database operations with upsert logic
│   ├── streamlit_streaming.py      # Real-time progress tracking
│   ├── main.py                     # CLI interface
│   ├── requirements.txt            # Python dependencies
│   └── test_*.py                   # Test suites
├── README.md                       # This file
└── OPTIMIZATION_REPORT.md          # Detailed performance improvements
```

## 🎨 **Screenshots**

### Dashboard Overview
![Dashboard](https://via.placeholder.com/800x400/2c3e50/ffffff?text=Dashboard+Overview)

### SMA Breakout Opportunities
![Breakouts](https://via.placeholder.com/800x400/27ae60/ffffff?text=SMA+Breakout+Opportunities)

### Real-time Data Fetching
![Streaming](https://via.placeholder.com/800x400/f39c12/ffffff?text=Real-time+Progress+Updates)

## 📝 **License**

This project is open source and available under the MIT License.

## 🤝 **Contributing**

Contributions are welcome! Please feel free to submit a Pull Request.

## ❓ **Frequently Asked Questions**

### **Q: How often should I refresh the data?**
A: For day trading, refresh 2-3 times per day. For swing trading, once daily is sufficient.

### **Q: What's the difference between "Fresh Breakout" and "Holding Above"?**
A: "Fresh Breakout" means the stock broke above SMA TODAY (immediate action signal). "Holding Above" means it's been above SMA and maintaining (monitor for continuation).

### **Q: Why focus on ±5% of SMA instead of all stocks above SMA?**
A: Stocks already 8-10% above SMA are extended and risky to enter. The ±5% range catches opportunities before they become overextended.

### **Q: Can I use this for other markets besides NSE?**
A: Currently optimized for NSE stocks, but the logic can be adapted for other markets supported by yfinance.

### **Q: How accurate are the breakout signals?**
A: This is a screening tool, not a prediction system. Always combine with your own analysis, risk management, and market context.

## 📞 **Support**

- **Issues**: Open an issue in the repository
- **Feature Requests**: Submit via GitHub issues
- **Live App**: [https://smartink.streamlit.app/](https://smartink.streamlit.app/)

## 🌟 **Star History**

If you find SmartInk useful, please consider giving it a star! ⭐

---

## ⚠️ **Important Disclaimer**

This application is for **educational and informational purposes only**. It is **NOT financial advice**.

- Always do your own research
- Consult with qualified financial advisors
- Never risk more than you can afford to lose
- Past performance doesn't guarantee future results
- Markets can be volatile and unpredictable

## 🎯 **Mission Statement**

**Built for traders who want to catch opportunities early, not chase moves that already happened.**

SmartInk empowers traders with actionable intelligence, focusing on fresh breakouts and setups rather than extended moves. We believe in quality over quantity - showing you fewer, better opportunities instead of overwhelming you with noise.

**Happy Trading! 📈✨**
