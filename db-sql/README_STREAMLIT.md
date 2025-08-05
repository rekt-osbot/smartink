# 📈 Streamlit Stock Technical Analysis Dashboard

A modern, user-friendly web interface for stock technical analysis and screening. This replaces the CLI interface with an intuitive web-based dashboard that's perfect for users who prefer visual interfaces.

## 🚀 Features

### 📊 Dashboard Overview
- **Real-time metrics** showing total stocks, momentum indicators, and breakout patterns
- **Interactive pie charts** showing stock distribution above/below SMA
- **Top performers chart** highlighting best-performing stocks
- **Auto-refresh capability** for live data updates

### 📈 Stocks Above SMA Analysis
- **Filterable table** with minimum percentage thresholds
- **Progress bars** showing percentage above SMA visually
- **Export functionality** to download results as CSV
- **Interactive metrics** with averages and maximums

### 🚀 Breakout Pattern Detection
- **Scatter plot visualization** of breakout performance
- **Detailed pattern analysis** with yesterday vs today comparisons
- **Color-coded charts** for easy pattern identification
- **Export capabilities** for further analysis

### 📋 Data Explorer
- **Raw data viewer** with stock selection
- **Interactive price charts** using Plotly
- **Multi-stock comparison** capabilities
- **Data overview metrics** and statistics

## 🎯 How to Use

### Method 1: Direct Launch
```bash
# Navigate to the project directory
cd db-sql

# Run the Streamlit app
uv run streamlit run streamlit_app.py

# Or use the batch file
run_streamlit_dashboard.bat
```

### Method 2: Through Main Application
```bash
# Run the main application
uv run python main.py

# Select option 4: "Launch Web Dashboard (Streamlit)"
```

## 🖥️ Interface Guide

### Sidebar Controls
- **🔄 Fetch Latest Data**: Updates stock data from Yahoo Finance
- **🧭 Navigation**: Switch between different analysis views
- **⚙️ Settings**: Configure SMA periods and auto-refresh

### Main Dashboard Pages

#### 1. 📊 Dashboard Overview
- Quick metrics and summary statistics
- Visual distribution charts
- Top performer rankings

#### 2. 📈 Stocks Above SMA
- Detailed list of momentum stocks
- Filtering and sorting capabilities
- Export functionality

#### 3. 🚀 Breakout Patterns
- Open=high pattern detection
- Visual breakout analysis
- Performance metrics

#### 4. 📋 Data Explorer
- Raw data examination
- Multi-stock price charts
- Data quality overview

## 🎨 User Experience Features

### Visual Design
- **Clean, modern interface** with intuitive navigation
- **Color-coded metrics** for quick understanding
- **Responsive layout** that works on different screen sizes
- **Professional styling** with custom CSS

### Interactive Elements
- **Real-time charts** with zoom and pan capabilities
- **Filterable tables** with search and sort
- **Progress indicators** for data loading
- **Export buttons** for data download

### User-Friendly Features
- **Progress bars** showing data fetch status
- **Success/warning messages** for user feedback
- **Tooltips and help text** for guidance
- **Auto-refresh options** for live monitoring

## 📊 Chart Types

### Plotly Interactive Charts
- **Pie charts** for distribution analysis
- **Bar charts** for performance comparison
- **Scatter plots** for pattern visualization
- **Line charts** for price trends

### Streamlit Native Elements
- **Metrics cards** with delta indicators
- **Progress columns** in data tables
- **Multi-select widgets** for filtering
- **Slider controls** for parameter adjustment

## 🔧 Technical Details

### Dependencies
- **Streamlit 1.47.1**: Web framework
- **Plotly 6.2.0**: Interactive charts
- **Altair 5.5.0**: Additional visualization
- **Pandas**: Data manipulation
- **yfinance**: Stock data fetching

### Performance Optimizations
- **Session state management** for data persistence
- **Caching mechanisms** to avoid redundant API calls
- **Lazy loading** of expensive operations
- **Efficient data filtering** and display

### Browser Compatibility
- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Mobile browsers**: Responsive design

## 🚀 Getting Started

1. **Install dependencies** (if not already done):
   ```bash
   uv pip install streamlit==1.47.1 plotly==6.2.0 altair==5.5.0
   ```

2. **Launch the dashboard**:
   ```bash
   uv run streamlit run streamlit_app.py
   ```

3. **Open your browser** to: http://localhost:8501

4. **Fetch data** using the sidebar button

5. **Explore** the different analysis views

## 💡 Tips for Best Experience

### First Time Setup
1. Click "🔄 Fetch Latest Data" in the sidebar
2. Wait for data to load (shows progress)
3. Explore different pages using navigation
4. Adjust settings as needed

### Regular Usage
- Use auto-refresh for live monitoring
- Export data for external analysis
- Filter results based on your criteria
- Compare multiple stocks in Data Explorer

### Performance Tips
- Limit stock selections in Data Explorer
- Use filters to reduce data load
- Close unused browser tabs
- Refresh data periodically for accuracy

## 🔄 Data Updates

### Automatic Updates
- **Auto-refresh**: 30-second intervals (optional)
- **Session persistence**: Data survives page refreshes
- **Real-time metrics**: Updated with each data fetch

### Manual Updates
- **Fetch button**: Updates all stock data
- **Progress tracking**: Shows fetch status
- **Error handling**: Graceful failure management

## 📱 Mobile Experience

The dashboard is fully responsive and works well on:
- **Tablets**: Full functionality
- **Smartphones**: Optimized layout
- **Desktop**: Best experience

## 🎯 Perfect For

- **Beginner traders** who want visual interfaces
- **Technical analysts** needing quick screening
- **Portfolio managers** monitoring multiple stocks
- **Anyone** who prefers web interfaces over CLI

The Streamlit dashboard makes stock analysis accessible and enjoyable for users of all technical levels!
