@echo off
echo ========================================
echo   Stock Technical Analysis Dashboard
echo ========================================
echo.
echo Starting Streamlit web dashboard...
echo Open your browser to: http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard
echo ========================================
echo.

cd /d "%~dp0"
uv run streamlit run streamlit_app.py --server.port 8501 --server.address localhost

pause
