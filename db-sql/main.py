#!/usr/bin/env python3
"""
Main entry point for the NSE Tradable Stocks Database Application.
This provides a guided workflow for the entire application.
"""

import sys
import subprocess
from pathlib import Path

from utils import clear_screen, print_section_header, print_step
from config import APP_TITLE, CONSOLE_WIDTH
from data_processor import DataProcessor
from database_manager import DatabaseManager


class NSEStocksApp:
    """Main application class that orchestrates the entire workflow."""
    
    def __init__(self):
        """Initialize the application."""
        self.data_processor = DataProcessor(verbose=True)
        self.db_manager = DatabaseManager(verbose=True)
    
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.

        Returns:
            bool: True if all dependencies are available
        """
        print_step(1, "Checking Dependencies")

        required_modules = [
            'pandas', 'sqlite3', 'requests', 'tabulate', 'yfinance', 'numpy'
        ]
        
        missing_modules = []
        
        import importlib.util

        for module in required_modules:
            try:
                # Use lightweight module existence check
                spec = importlib.util.find_spec(module)
                if spec is None:
                    print(f"✗ {module} (missing)")
                    missing_modules.append(module)
                else:
                    print(f"✓ {module}")
            except (ImportError, ValueError, ModuleNotFoundError):
                print(f"✗ {module} (missing)")
                missing_modules.append(module)
        
        if missing_modules:
            print(f"\nMissing dependencies: {', '.join(missing_modules)}")
            print("Please install them using: pip install -r requirements.txt")
            return False
        
        print("\n✓ All dependencies are available!")
        return True
    
    def prompt_data_refresh(self) -> bool:
        """
        Ask user if they want to download fresh data.
        
        Returns:
            bool: True if user wants to refresh data
        """
        print_step(2, "Data Source Selection")
        
        # Check if database already exists and has data
        if self.db_manager.table_exists():
            record_count = self.db_manager.get_record_count()
            if record_count > 0:
                print(f"Existing database found with {record_count} records.")
        
        print("\nData source options:")
        print("1. Use existing data (if available)")
        print("2. Download fresh data from NSE")
        print("3. Load from local CSV files")
        
        while True:
            choice = input("\nSelect option (1-3): ").strip()
            if choice == '1':
                return False  # Don't refresh
            elif choice == '2':
                return True   # Download fresh
            elif choice == '3':
                return False  # Use local files
            else:
                print("Please enter 1, 2, or 3")
    
    def setup_database(self, refresh_data: bool = False) -> bool:
        """
        Set up the database with data.
        
        Args:
            refresh_data (bool): Whether to download fresh data
            
        Returns:
            bool: True if setup successful
        """
        print_step(3, "Database Setup")
        
        # Check if we can use existing data
        if not refresh_data and self.db_manager.table_exists():
            record_count = self.db_manager.get_record_count()
            if record_count > 0:
                print(f"Using existing database with {record_count} records.")
                return True
        
        # Load data
        print("Loading data...")
        df, source = self.data_processor.load_data_with_fallback()
        
        if df is None:
            print("✗ Failed to load data from any source")
            return False
        
        print(f"✓ Data loaded from {source}")
        
        # Clean the data
        print("Cleaning data...")
        cleaned_df = self.data_processor.clean_dataframe(df)
        
        # Show data summary
        self.data_processor.print_data_summary(cleaned_df, "Cleaned Data Summary")

        # Create and populate database table in one optimized operation
        print("\nCreating and populating database table...")
        if not self.db_manager.create_and_populate_table(cleaned_df):
            print("✗ Failed to create and populate database table")
            return False
        
        print("✓ Database setup completed successfully!")
        return True
    
    def launch_interface(self):
        """Launch the database query interface."""
        print_step(4, "Launching Interface")

        try:
            # Import and run the enhanced interface
            from db_interface_enhanced import main as run_interface
            print("Starting the database query interface...")
            print("(Press Ctrl+C to return to this menu)\n")
            run_interface()

        except KeyboardInterrupt:
            print("\n\nReturned to main menu.")
        except ImportError as e:
            print(f"✗ Error importing interface: {e}")
        except Exception as e:
            print(f"✗ Error launching interface: {e}")

    def launch_stock_dashboard(self):
        """Launch the stock technical analysis dashboard."""
        print_step(5, "Launching Stock Dashboard")

        try:
            # Import and run the stock dashboard
            from stock_dashboard import main as run_dashboard
            print("Starting the stock technical analysis dashboard...")
            print("(Press Ctrl+C to return to this menu)\n")
            run_dashboard()

        except KeyboardInterrupt:
            print("\n\nReturned to main menu.")
        except ImportError as e:
            print(f"✗ Error importing dashboard: {e}")
        except Exception as e:
            print(f"✗ Error launching dashboard: {e}")

    def launch_streamlit_dashboard(self):
        """Launch the Streamlit web dashboard."""
        print_step(6, "Launching Streamlit Web Dashboard")

        try:
            import subprocess
            import webbrowser
            import time

            print("Starting Streamlit web dashboard...")
            print("Dashboard will open in your default web browser.")
            print("URL: http://localhost:8501")
            print("(Press Ctrl+C to stop the dashboard)\n")

            # Start Streamlit in a subprocess
            process = subprocess.Popen([
                "uv", "run", "streamlit", "run", "streamlit_app.py",
                "--server.port", "8501",
                "--server.address", "localhost"
            ])

            # Wait a moment for Streamlit to start
            time.sleep(3)

            # Open browser
            try:
                webbrowser.open("http://localhost:8501")
            except:
                pass  # Browser opening is optional

            # Wait for process to complete
            process.wait()

        except KeyboardInterrupt:
            print("\n\nStopping Streamlit dashboard...")
            try:
                process.terminate()
            except:
                pass
            print("Returned to main menu.")
        except ImportError as e:
            print(f"✗ Error importing required modules: {e}")
        except Exception as e:
            print(f"✗ Error launching Streamlit dashboard: {e}")
    
    def show_main_menu(self):
        """Display the main application menu."""
        while True:
            clear_screen()
            print_section_header(APP_TITLE, CONSOLE_WIDTH)
            
            print("Main Menu:")
            print("1. Setup/Refresh Database")
            print("2. Launch Query Interface")
            print("3. Launch Stock Dashboard (CLI)")
            print("4. Launch Web Dashboard (Streamlit)")
            print("5. Check System Status")
            print("6. Exit")
            print("-" * 30)
            
            choice = input("Select option (1-6): ").strip()

            if choice == '1':
                refresh = self.prompt_data_refresh()
                if self.setup_database(refresh):
                    input("\nPress Enter to continue...")
                else:
                    input("\nSetup failed. Press Enter to continue...")

            elif choice == '2':
                if not self.db_manager.table_exists():
                    print("Database not found. Please setup database first.")
                    input("Press Enter to continue...")
                else:
                    self.launch_interface()

            elif choice == '3':
                self.launch_stock_dashboard()

            elif choice == '4':
                self.launch_streamlit_dashboard()

            elif choice == '5':
                self.show_system_status()
                input("\nPress Enter to continue...")

            elif choice == '6':
                print("Goodbye!")
                break

            else:
                print("Please enter a number between 1 and 6")
                input("Press Enter to continue...")
    
    def show_system_status(self):
        """Display current system status."""
        print_section_header("System Status", CONSOLE_WIDTH)
        
        # Check dependencies
        print("Dependencies:")
        self.check_dependencies()
        
        # Check database
        print(f"\nDatabase Status:")
        if self.db_manager.table_exists():
            record_count = self.db_manager.get_record_count()
            print(f"✓ Database exists with {record_count} records")
            
            # Show table info
            table_info = self.db_manager.get_table_info()
            if table_info:
                print(f"✓ Table schema: {len(table_info)} columns")
                for col_info in table_info:
                    print(f"  - {col_info[1]} ({col_info[2]})")
        else:
            print("✗ Database not found")
        
        # Check files
        print(f"\nFile Status:")
        db_path = Path(self.db_manager.db_file)
        print(f"Database file: {db_path.absolute()}")
        print(f"  Exists: {'✓' if db_path.exists() else '✗'}")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
    
    def run(self):
        """Run the main application."""
        try:
            # Initial setup check
            if not self.check_dependencies():
                input("\nPress Enter to exit...")
                return
            
            # Show main menu
            self.show_main_menu()
            
        except KeyboardInterrupt:
            print("\n\nApplication interrupted by user.")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            input("Press Enter to exit...")


def main():
    """Main entry point."""
    app = NSEStocksApp()
    app.run()


if __name__ == "__main__":
    main()
