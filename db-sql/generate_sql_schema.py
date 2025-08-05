"""
SQL schema generation module - now uses the unified database manager.
This module maintains backward compatibility while using the new modular architecture.
"""

from data_processor import DataProcessor
from database_manager import DatabaseManager
from utils import print_section_header

# Redundant functions removed - now using DatabaseManager for all schema operations

# create_database_table function removed - now using DatabaseManager.create_table_from_dataframe()

def main():
    """
    Main function to load CSV data and create SQL schema
    """
    print("Step 6: Generate a matching SQL schema")
    print("=" * 50)
    
    # Try to load data from the sample CSV first
    csv_files = ["sample_with_dates.csv", r"C:\Users\chandan.gupta1\.cache\nse_analyzer\nifty_500_stocks.csv"]
    
    df = None
    csv_used = None
    
    for csv_path in csv_files:
        if Path(csv_path).exists():
            print(f"Loading CSV file: {csv_path}")
            try:
                # Load the CSV into DataFrame
                df = pd.read_csv(csv_path)
                
                # Strip and normalize column names to snake_case
                original_columns = df.columns.tolist()
                df.columns = [normalize_column_name(col) for col in df.columns]
                
                print(f"Column name transformations:")
                for orig, new in zip(original_columns, df.columns):
                    if orig != new:
                        print(f"  '{orig}' -> '{new}'")
                
                # Convert date columns to datetime if they exist
                date_columns = [col for col in df.columns if 'date_of_listing' in col.lower()]
                if date_columns:
                    for date_col in date_columns:
                        print(f"Converting '{date_col}' to datetime64[ns]...")
                        df[date_col] = pd.to_datetime(df[date_col])
                        print(f"  Data type after conversion: {df[date_col].dtype}")
                
                csv_used = csv_path
                break
                
            except Exception as e:
                print(f"Error loading {csv_path}: {e}")
                continue
    
    if df is None:
        print("No valid CSV file found. Creating a sample DataFrame for demonstration...")
        # Create a sample DataFrame that matches the expected structure
        df = pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS', 'HDFCBANK'],
            'company_name': ['Reliance Industries Ltd.', 'Tata Consultancy Services Ltd.', 'HDFC Bank Ltd.'],
            'industry': ['Oil Gas & Consumable Fuels', 'Information Technology', 'Financial Services'],
            'date_of_listing': pd.to_datetime(['1995-11-29', '2004-08-25', '1995-11-08'])
        })
    
    print(f"\nDataFrame shape: {df.shape}")
    print(f"DataFrame columns: {list(df.columns)}")
    print(f"\nDataFrame dtypes:")
    print(df.dtypes)
    print(f"\nDataFrame head:")
    print(df.head())
    
    # Generate the CREATE TABLE SQL using the new database manager
    db_manager = DatabaseManager(verbose=True)
    create_table_sql = db_manager.generate_create_table_sql(df)

    print(f"\n" + "="*60)
    print("GENERATED SQL SCHEMA:")
    print("="*60)
    print(create_table_sql)

    # Optionally create the database and table
    create_database = input("\nDo you want to create the database table? (y/n): ").lower().strip()
    if create_database == 'y':
        if db_manager.create_table_from_dataframe(df):
            print("✓ Database table created successfully!")
        else:
            print("✗ Failed to create database table")

    print(f"\n" + "="*60)
    print("Schema generation completed!")
    print("="*60)

if __name__ == "__main__":
    main()
