"""
Data loading and cleaning module - now a wrapper around the unified data processor.
This module maintains backward compatibility while using the new modular architecture.
"""

from data_processor import DataProcessor
from utils import ensure_file_exists

def load_and_clean_data(csv_path):
    """
    Load CSV data into DataFrame and clean it according to specifications.
    This function now uses the unified DataProcessor for consistency.

    Args:
        csv_path (str): Path to the CSV file to load

    Returns:
        pd.DataFrame: Cleaned DataFrame

    Raises:
        FileNotFoundError: If the CSV file doesn't exist
    """
    # Ensure file exists
    ensure_file_exists(csv_path, "CSV file")

    # Initialize data processor
    data_processor = DataProcessor(verbose=True)

    # Load the CSV file
    df = data_processor.load_csv_from_file(csv_path)

    if df is None:
        raise RuntimeError(f"Failed to load CSV file: {csv_path}")

    # Clean the DataFrame
    cleaned_df = data_processor.clean_dataframe(df)

    # Print summary information
    data_processor.print_data_summary(cleaned_df, f"Loaded and Cleaned Data from {csv_path}")

    return cleaned_df

if __name__ == "__main__":
    import sys
    import argparse
    from config import LOCAL_CSV_FILES

    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Load and clean CSV data for NSE stocks')
    parser.add_argument('csv_file', nargs='?', help='Path to the CSV file to load')
    parser.add_argument('--list-defaults', action='store_true',
                       help='List default CSV files that will be tried')

    args = parser.parse_args()

    if args.list_defaults:
        print("Default CSV files that will be tried (in order):")
        for i, file_path in enumerate(LOCAL_CSV_FILES, 1):
            print(f"  {i}. {file_path}")
        sys.exit(0)

    # Determine which CSV file to use
    if args.csv_file:
        csv_file_path = args.csv_file
    else:
        # Try default files
        csv_file_path = None
        for file_path in LOCAL_CSV_FILES:
            from pathlib import Path
            if Path(file_path).exists():
                csv_file_path = file_path
                print(f"Using default file: {csv_file_path}")
                break

        if not csv_file_path:
            print("No CSV file specified and no default files found.")
            print(f"Tried: {', '.join(LOCAL_CSV_FILES)}")
            print("\nUsage:")
            print(f"  python {sys.argv[0]} <csv_file_path>")
            print(f"  python {sys.argv[0]} --list-defaults")
            sys.exit(1)

    try:
        # Load and clean the data
        df = load_and_clean_data(csv_file_path)

        # Additional info about the loaded data
        print(f"\nSummary:")
        print(f"Successfully loaded {df.shape[0]} rows and {df.shape[1]} columns")

        # If there are any missing values, report them
        missing_data = df.isnull().sum()
        if missing_data.any():
            print(f"\nMissing values per column:")
            print(missing_data[missing_data > 0])
        else:
            print(f"\nNo missing values found in the dataset")

    except Exception as e:
        print(f"Error loading data: {e}")
        print("Please check the file path and ensure the CSV file exists.")
