"""
NSE data download module - now uses the unified data processing and database management modules.
This module maintains backward compatibility while using the new modular architecture.
"""

from data_processor import DataProcessor
from database_manager import DatabaseManager
from config import BHAV_CSV_URL
from utils import print_section_header


def download_and_update_db():
    """
    Download NSE data and update the database using the new modular architecture.
    """
    print_section_header("Download and Update NSE Data")

    # Initialize processors
    data_processor = DataProcessor(verbose=True)
    db_manager = DatabaseManager(verbose=True)

    try:
        print(f"Fetching data from {BHAV_CSV_URL}...")

        # Download data using the data processor
        df = data_processor.load_csv_from_url(BHAV_CSV_URL)

        if df is None:
            print("✗ Failed to download data")
            return False

        print("✓ Data fetched successfully.")

        # Clean the data
        print("Cleaning data...")
        cleaned_df = data_processor.clean_dataframe(df)

        # Show data summary
        data_processor.print_data_summary(cleaned_df, "Downloaded Data Summary")

        # Create and populate database table in one optimized operation
        print("Creating and updating database...")
        if not db_manager.create_and_populate_table(cleaned_df):
            print("✗ Failed to create and update database")
            return False

        print("✓ Database updated with new data.")
        return True

    except Exception as e:
        print(f"✗ An error occurred: {e}")
        return False


def main():
    """Main entry point."""
    success = download_and_update_db()
    if not success:
        print("\n✗ Failed to download and update database")
        input("Press Enter to exit...")
    else:
        print("\n✓ Successfully downloaded and updated database")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
