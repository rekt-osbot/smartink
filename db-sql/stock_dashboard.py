"""
Interactive stock dashboard for technical analysis and screening.
This module provides a user-friendly interface for stock analysis.
"""

import sys
from datetime import datetime
from typing import Optional

from utils import clear_screen, print_section_header
from config import APP_TITLE, CONSOLE_WIDTH
from technical_analysis import TechnicalAnalyzer


class StockDashboard:
    """Interactive dashboard for stock technical analysis."""
    
    def __init__(self):
        """Initialize the stock dashboard."""
        self.analyzer = TechnicalAnalyzer(verbose=True)
        self.data_fetched = False
    
    def print_header(self):
        """Print the dashboard header."""
        print_section_header("STOCK TECHNICAL ANALYSIS DASHBOARD", CONSOLE_WIDTH)
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * CONSOLE_WIDTH)
    
    def print_menu(self):
        """Display the main dashboard menu."""
        print("\n--- DASHBOARD MENU ---")
        print("1. Fetch Latest Stock Data")
        print("2. Show Stocks Above 20-Day SMA")
        print("3. Show Open=High Breakout Patterns")
        print("4. Display Summary Statistics")
        print("5. Export Results to CSV")
        print("6. Setup Database Schema")
        print("7. Clean Up Old Data")
        print("8. Back to Main Menu")
        print("-" * 25)
    
    def fetch_latest_data(self):
        """Fetch and store latest stock data."""
        print_section_header("FETCHING LATEST STOCK DATA", CONSOLE_WIDTH)

        print("This will fetch the latest 3 months of data for popular NSE stocks.")
        print("Using curated list of stocks that work well with Yahoo Finance.")
        print("Note: Limited to ~30 popular stocks to ensure reliability.")

        confirm = input("\nProceed with data fetch? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Data fetch cancelled.")
            return

        print("\nFetching data... This may take a few minutes.")
        print("Please wait...")

        try:
            # Setup database schema first
            if not self.analyzer.setup_database():
                print("✗ Failed to setup database schema")
                return

            # Fetch and store data using popular stocks only
            if self.analyzer.fetch_and_store_data(use_popular_only=True):
                print("✓ Data fetch completed successfully!")
                self.data_fetched = True
            else:
                print("✗ Data fetch failed")

        except KeyboardInterrupt:
            print("\n\nData fetch interrupted by user.")
        except Exception as e:
            print(f"\nError during data fetch: {e}")
    
    def show_stocks_above_sma(self):
        """Display stocks above 20-day SMA."""
        clear_screen()
        self.analyzer.display_stocks_above_sma(20)
        
        # Ask if user wants to see different SMA period
        print("\nOptions:")
        print("1. Show 50-day SMA instead")
        print("2. Return to menu")
        
        choice = input("\nSelect option (1-2): ").strip()
        if choice == '1':
            clear_screen()
            self.analyzer.display_stocks_above_sma(50)
    
    def show_open_high_patterns(self):
        """Display open=high breakout patterns."""
        clear_screen()
        self.analyzer.display_open_high_patterns()
    
    def show_summary_statistics(self):
        """Display summary statistics."""
        clear_screen()
        self.analyzer.display_summary()
    
    def export_results(self):
        """Export analysis results to CSV files."""
        print_section_header("EXPORT RESULTS", CONSOLE_WIDTH)
        
        print("This will export the current analysis results to CSV files:")
        print("• stocks_above_20_sma.csv")
        print("• open_high_patterns.csv")
        
        confirm = input("\nProceed with export? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Export cancelled.")
            return
        
        if self.analyzer.export_results_to_csv():
            print("✓ Results exported successfully!")
        else:
            print("✗ Export failed")
    
    def setup_database_schema(self):
        """Setup the extended database schema."""
        print_section_header("DATABASE SCHEMA SETUP", CONSOLE_WIDTH)
        
        print("This will create the extended database tables for storing:")
        print("• Stock price data (OHLCV)")
        print("• Technical indicators (SMA, etc.)")
        
        confirm = input("\nProceed with schema setup? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Schema setup cancelled.")
            return
        
        if self.analyzer.setup_database():
            print("✓ Database schema setup completed!")
        else:
            print("✗ Database schema setup failed")
    
    def cleanup_old_data(self):
        """Clean up old data from the database."""
        print_section_header("CLEAN UP OLD DATA", CONSOLE_WIDTH)
        
        print("This will remove price and indicator data older than specified days.")
        print("This helps keep the database size manageable.")
        
        try:
            days = input("\nEnter number of days to keep (default 90): ").strip()
            days_to_keep = int(days) if days else 90
            
            if days_to_keep < 30:
                print("Minimum 30 days required.")
                return
            
            confirm = input(f"\nDelete data older than {days_to_keep} days? (y/n): ").lower().strip()
            if confirm != 'y':
                print("Cleanup cancelled.")
                return
            
            if self.analyzer.cleanup_old_data(days_to_keep):
                print("✓ Old data cleaned up successfully!")
            else:
                print("✗ Cleanup failed")
                
        except ValueError:
            print("Invalid number entered.")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def check_data_availability(self) -> bool:
        """
        Check if data is available for analysis.
        
        Returns:
            bool: True if data is available
        """
        stats = self.analyzer.get_summary_statistics()
        return stats.get('total_stocks_with_data', 0) > 0
    
    def show_data_warning(self):
        """Show warning when no data is available."""
        print("\n" + "!" * 50)
        print("WARNING: No stock data found in database!")
        print("Please run 'Fetch Latest Stock Data' first.")
        print("!" * 50)
    
    def run(self):
        """Run the main dashboard loop."""
        try:
            while True:
                clear_screen()
                self.print_header()
                
                # Check if data is available
                has_data = self.check_data_availability()
                if not has_data and not self.data_fetched:
                    self.show_data_warning()
                
                self.print_menu()
                
                choice = input("Select option (1-8): ").strip()
                
                if choice == '1':
                    self.fetch_latest_data()
                    input("\nPress Enter to continue...")
                
                elif choice == '2':
                    if has_data:
                        self.show_stocks_above_sma()
                    else:
                        self.show_data_warning()
                    input("\nPress Enter to continue...")
                
                elif choice == '3':
                    if has_data:
                        self.show_open_high_patterns()
                    else:
                        self.show_data_warning()
                    input("\nPress Enter to continue...")
                
                elif choice == '4':
                    self.show_summary_statistics()
                    input("\nPress Enter to continue...")
                
                elif choice == '5':
                    if has_data:
                        self.export_results()
                    else:
                        self.show_data_warning()
                    input("\nPress Enter to continue...")
                
                elif choice == '6':
                    self.setup_database_schema()
                    input("\nPress Enter to continue...")
                
                elif choice == '7':
                    if has_data:
                        self.cleanup_old_data()
                    else:
                        self.show_data_warning()
                    input("\nPress Enter to continue...")
                
                elif choice == '8':
                    print("Returning to main menu...")
                    break
                
                else:
                    print("Please enter a number between 1 and 8")
                    input("Press Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\nDashboard interrupted by user.")
        except Exception as e:
            print(f"\nUnexpected error in dashboard: {e}")
            input("Press Enter to continue...")


def main():
    """Main entry point for the dashboard."""
    dashboard = StockDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
