"""
Database population script using the unified data processing and database management modules.
This script is now a thin wrapper around the new modular architecture.
"""

from data_processor import DataProcessor
from database_manager import DatabaseManager
from utils import print_section_header

def populate_database():
    """
    Load CSV data and populate the database using the new modular architecture.
    """
    print_section_header("Populate Database with Cleaned Data")

    # Initialize processors
    data_processor = DataProcessor(verbose=True)
    db_manager = DatabaseManager(verbose=True)

    # Load data with fallback strategy
    print("Loading data...")
    df, source = data_processor.load_data_with_fallback()

    if df is None:
        print("✗ Error: No valid data source found!")
        return False

    print(f"✓ Successfully loaded data from {source}")

    # Clean the data
    print("\nCleaning data...")
    cleaned_df = data_processor.clean_dataframe(df)

    # Show data summary
    data_processor.print_data_summary(cleaned_df, "Cleaned Data Summary")

    # Create and populate database table in one optimized operation
    print("\nCreating and populating database table...")
    if not db_manager.create_and_populate_table(cleaned_df):
        print("✗ Failed to create and populate database table")
        return False

    print("\n✓ Database population completed successfully!")
    return True

if __name__ == "__main__":
    success = populate_database()
    if not success:
        print("\n✗ Failed to populate database")
    input("\nPress Enter to exit...")
