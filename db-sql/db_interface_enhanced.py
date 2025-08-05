import sqlite3
from tabulate import tabulate
from datetime import datetime

from utils import clear_screen, print_section_header
from config import APP_TITLE, CONSOLE_WIDTH, DB_FILE, TABLE_NAME
from database_manager import DatabaseManager

def print_header():
    """Print the application header"""
    print_section_header("TRADABLE STOCKS DATABASE QUERY INTERFACE", CONSOLE_WIDTH)

def print_menu():
    """Display the main menu"""
    print("\n--- MENU OPTIONS ---")
    print("1. Show all stocks")
    print("2. Search stocks by symbol")
    print("3. Search stocks by industry")
    print("4. Show database schema")
    print("5. Execute custom SQL query")
    print("6. Count total stocks")
    print("7. Exit")
    print("-" * 20)

def find_matching_column(db_manager, possible_columns, column_type="column"):
    """
    Dynamically find which of the possible columns actually exist in the database.

    Args:
        db_manager: DatabaseManager instance
        possible_columns: List of possible column names to check
        column_type: Description of what type of column we're looking for (for error messages)

    Returns:
        str or None: The first matching column name, or None if none found
    """
    # Get actual table columns
    table_info = db_manager.get_table_info()
    if not table_info:
        return None

    actual_columns = [col[1].lower() for col in table_info]  # col[1] is the column name

    # Find intersection between possible and actual columns
    for possible_col in possible_columns:
        if possible_col.lower() in actual_columns:
            return possible_col.lower()

    return None

def execute_query(conn, query, params=None):
    """Execute a query and return results with column headers"""
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        if results:
            headers = [desc[0] for desc in cursor.description]
            return headers, results
        else:
            return None, []
    except sqlite3.Error as e:
        print(f"\nError executing query: {e}")
        return None, None

def show_all_stocks(db_manager):
    """Display all stocks in the database"""
    query = f"SELECT * FROM {TABLE_NAME}"
    result = db_manager.execute_query(query)

    if result and result[1]:
        headers, results = result
        print("\n=== ALL STOCKS ===")
        print(tabulate(results, headers=headers, tablefmt="grid"))
        print(f"\nTotal records: {len(results)}")
    else:
        print("\nNo stocks found in the database.")

def search_by_symbol(db_manager):
    """Search stocks by symbol"""
    symbol = input("\nEnter stock symbol (or partial symbol): ").strip().upper()

    # Dynamically find which symbol column exists
    possible_columns = ['symbol', 'stock_symbol', 'company_symbol', 'ticker']
    symbol_column = find_matching_column(db_manager, possible_columns, "symbol")

    if not symbol_column:
        print(f"\nNo symbol column found in database.")
        print(f"Looked for: {', '.join(possible_columns)}")

        # Show available columns to help user
        table_info = db_manager.get_table_info()
        if table_info:
            available_columns = [col[1] for col in table_info]
            print(f"Available columns: {', '.join(available_columns)}")
        return

    # Execute search using the found column
    query = f"SELECT * FROM {TABLE_NAME} WHERE {symbol_column} LIKE ?"
    result = db_manager.execute_query(query, (f"%{symbol}%",))

    if result and result[1]:
        headers, results = result
        print(f"\n=== STOCKS MATCHING '{symbol}' (searched in '{symbol_column}') ===")
        print(tabulate(results, headers=headers, tablefmt="grid"))
        print(f"\nFound {len(results)} matching record(s)")
    else:
        print(f"\nNo stocks found matching '{symbol}' in column '{symbol_column}'")

def search_by_industry(db_manager):
    """Search stocks by industry"""
    industry = input("\nEnter industry name (or partial name): ").strip()

    # Dynamically find which industry column exists
    possible_columns = ['industry', 'sector', 'business_segment', 'business_category']
    industry_column = find_matching_column(db_manager, possible_columns, "industry")

    if not industry_column:
        print(f"\nNo industry/sector column found in database.")
        print(f"Looked for: {', '.join(possible_columns)}")

        # Show available columns to help user
        table_info = db_manager.get_table_info()
        if table_info:
            available_columns = [col[1] for col in table_info]
            print(f"Available columns: {', '.join(available_columns)}")
        return

    # Execute search using the found column
    query = f"SELECT * FROM {TABLE_NAME} WHERE {industry_column} LIKE ?"
    result = db_manager.execute_query(query, (f"%{industry}%",))

    if result and result[1]:
        headers, results = result
        print(f"\n=== STOCKS IN '{industry}' INDUSTRY (searched in '{industry_column}') ===")
        print(tabulate(results, headers=headers, tablefmt="grid"))
        print(f"\nFound {len(results)} matching record(s)")
    else:
        print(f"\nNo stocks found matching '{industry}' in column '{industry_column}'")

def show_schema(db_manager):
    """Display the database schema"""
    schema_info = db_manager.get_table_info()

    if schema_info:
        print("\n=== DATABASE SCHEMA ===")
        print(f"\nTable: {TABLE_NAME}")
        print("-" * 50)

        headers = ["Column ID", "Name", "Type", "Not Null", "Default", "Primary Key"]
        print(tabulate(schema_info, headers=headers, tablefmt="grid"))
        print(f"\nTotal columns: {len(schema_info)}")
    else:
        print("\nError retrieving schema information.")

def execute_custom_query(db_manager):
    """Execute a custom SQL query"""
    print("\n=== CUSTOM SQL QUERY ===")
    print("Enter your SQL query (type 'cancel' to return to menu):")
    print(f"Example: SELECT * FROM {TABLE_NAME} LIMIT 10")
    query = input("> ").strip()

    if query.lower() == 'cancel':
        return

    if not query:
        print("Empty query entered.")
        return

    result = db_manager.execute_query(query)

    if result:
        headers, results = result
        if results:
            print("\nQuery Results:")
            print(tabulate(results, headers=headers, tablefmt="grid"))
            print(f"\nReturned {len(results)} row(s)")
        else:
            print("\nQuery executed successfully with no results.")
    else:
        print("\nError executing query.")

def count_stocks(db_manager):
    """Count total stocks in the database"""
    count = db_manager.get_record_count()

    if count >= 0:
        print(f"\n=== TOTAL STOCKS IN DATABASE: {count} ===")

        # Try to show count by industry if industry column exists
        possible_industry_cols = ['industry', 'sector', 'business_segment', 'business_category']
        industry_column = find_matching_column(db_manager, possible_industry_cols, "industry")

        if industry_column:
            query = f"""
                SELECT {industry_column}, COUNT(*) as count
                FROM {TABLE_NAME}
                GROUP BY {industry_column}
                ORDER BY count DESC
            """
            result = db_manager.execute_query(query)

            if result and result[1]:
                headers, results = result
                print(f"\n=== STOCKS BY {industry_column.upper()} ===")
                print(tabulate(results, headers=headers, tablefmt="grid"))
            else:
                print(f"\nNo data found for grouping by '{industry_column}'")
        else:
            print(f"\nNo industry/sector column found for grouping.")
            print(f"Looked for: {', '.join(possible_industry_cols)}")
    else:
        print("\nError counting stocks.")

def main():
    """Main application loop"""
    try:
        # Initialize database manager
        db_manager = DatabaseManager(DB_FILE, verbose=False)

        # Check if database exists and has data
        if not db_manager.table_exists():
            print(f"Error: Database table '{TABLE_NAME}' not found!")
            print("Please run the main application to setup the database first.")
            input("\nPress Enter to exit...")
            return

        record_count = db_manager.get_record_count()
        if record_count <= 0:
            print("Database table exists but contains no data.")
            print("Please run the main application to populate the database.")
            input("\nPress Enter to exit...")
            return

        while True:
            clear_screen()
            print_header()
            print_menu()

            choice = input("\nEnter your choice (1-7): ").strip()

            if choice == '1':
                show_all_stocks(db_manager)
            elif choice == '2':
                search_by_symbol(db_manager)
            elif choice == '3':
                search_by_industry(db_manager)
            elif choice == '4':
                show_schema(db_manager)
            elif choice == '5':
                execute_custom_query(db_manager)
            elif choice == '6':
                count_stocks(db_manager)
            elif choice == '7':
                print("\nThank you for using the Tradable Stocks Database Interface!")
                print("Goodbye!")
                break
            else:
                print("\nInvalid choice! Please select a number between 1 and 7.")

            if choice != '7':
                input("\nPress Enter to continue...")

    except Exception as e:
        print(f"\nFatal error: {e}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
