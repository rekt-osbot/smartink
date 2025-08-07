"""
Unified database management module for NSE stocks data.
This module handles all database operations including schema creation, connection management, and data population.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

from utils import print_step
from config import DB_FILE, TABLE_NAME, PANDAS_TO_SQLITE_TYPES, DATE_FORMAT


class DatabaseManager:
    """Handles all database operations with proper schema management."""
    
    def __init__(self, db_file: str = DB_FILE, verbose: bool = True):
        """
        Initialize the database manager.
        
        Args:
            db_file (str): Path to the SQLite database file
            verbose (bool): Whether to print detailed information
        """
        self.db_file = db_file
        self.verbose = verbose
        self.table_name = TABLE_NAME
    
    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def map_pandas_dtype_to_sqlite(self, dtype) -> str:
        """
        Map pandas dtype to appropriate SQLite type.
        
        Args:
            dtype: Pandas dtype
            
        Returns:
            str: SQLite type string
        """
        dtype_str = str(dtype)
        
        # Handle datetime types
        if 'datetime' in dtype_str:
            return 'DATE'
        
        # Use mapping from config
        return PANDAS_TO_SQLITE_TYPES.get(dtype_str, 'TEXT')
    
    def generate_create_table_sql(self, df: pd.DataFrame) -> str:
        """
        Generate CREATE TABLE SQL statement from DataFrame schema.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze
            
        Returns:
            str: CREATE TABLE SQL statement
        """
        columns_sql = []
        
        if self.verbose:
            self._log("Mapping pandas dtypes to SQLite types:")
            self._log("-" * 50)
        
        for column, dtype in df.dtypes.items():
            sqlite_type = self.map_pandas_dtype_to_sqlite(dtype)
            columns_sql.append(f"    {column} {sqlite_type}")
            
            if self.verbose:
                self._log(f"{column:20} | {str(dtype):15} -> {sqlite_type}")
        
        # Join all column definitions
        columns_definition = ",\n".join(columns_sql)
        
        # Build the complete CREATE TABLE statement
        create_table_sql = f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
{columns_definition}
);"""
        
        return create_table_sql
    
    def create_table_from_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Create database table based on DataFrame schema.
        
        Args:
            df (pd.DataFrame): DataFrame to base schema on
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            create_sql = self.generate_create_table_sql(df)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Drop existing table
                cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                self._log(f"Dropped existing table: {self.table_name}")
                
                # Create new table
                cursor.execute(create_sql)
                self._log(f"Created table: {self.table_name}")
                
                if self.verbose:
                    self._log("\nGenerated SQL:")
                    self._log(create_sql)
                
                conn.commit()
                return True
                
        except Exception as e:
            self._log(f"Error creating table: {e}")
            return False
    
    def populate_table(self, df: pd.DataFrame, if_exists: str = 'append') -> bool:
        """
        Populate the database table with DataFrame data.

        Args:
            df (pd.DataFrame): DataFrame containing data to insert
            if_exists (str): How to behave if table exists ('append', 'replace', 'fail')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare DataFrame for database insertion
            df_to_insert = df.copy()

            # Convert datetime columns to string format for SQLite
            for col in df_to_insert.columns:
                if df_to_insert[col].dtype == 'datetime64[ns]':
                    df_to_insert[col] = df_to_insert[col].dt.strftime(DATE_FORMAT)
                    self._log(f"Converted {col} to date string format")

            with self.get_connection() as conn:
                # Use pandas to_sql for efficient insertion
                df_to_insert.to_sql(
                    self.table_name,
                    conn,
                    if_exists=if_exists,
                    index=False
                )

                # Verify insertion
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                count = cursor.fetchone()[0]

                self._log(f"Successfully inserted {count} records into {self.table_name}")

                # Show sample data
                if self.verbose:
                    self._show_sample_data(cursor)

                conn.commit()
                return True

        except Exception as e:
            self._log(f"Error populating table: {e}")
            return False

    def create_and_populate_table(self, df: pd.DataFrame, table_name: Optional[str] = None) -> bool:
        """
        Optimized method to create table and populate it in one operation.
        This avoids the redundant DROP+CREATE operations.

        Args:
            df (pd.DataFrame): DataFrame to create table from and populate
            table_name (Optional[str]): Name of the table to create. Defaults to self.table_name.

        Returns:
            bool: True if successful, False otherwise
        """
        target_table = table_name if table_name is not None else self.table_name
        try:
            # Prepare DataFrame for database insertion
            df_to_insert = df.copy()

            # Convert datetime columns to string format for SQLite
            for col in df_to_insert.columns:
                if df_to_insert[col].dtype == 'datetime64[ns]':
                    df_to_insert[col] = df_to_insert[col].dt.strftime(DATE_FORMAT)
                    self._log(f"Converted {col} to date string format")

            # Show schema mapping if verbose
            if self.verbose:
                self._log("Mapping pandas dtypes to SQLite types:")
                self._log("-" * 50)
                for column, dtype in df.dtypes.items():
                    sqlite_type = self.map_pandas_dtype_to_sqlite(dtype)
                    self._log(f"{column:20} | {str(dtype):15} -> {sqlite_type}")

            with self.get_connection() as conn:
                # Use pandas to_sql with 'replace' - this handles everything efficiently
                df_to_insert.to_sql(
                    target_table,
                    conn,
                    if_exists='replace',
                    index=False
                )

                # Verify insertion
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
                count = cursor.fetchone()[0]

                self._log(f"Successfully created table '{target_table}' and inserted {count} records")

                # Show sample data
                if self.verbose:
                    self._show_sample_data(cursor, table_name=target_table)

                conn.commit()
                return True

        except Exception as e:
            self._log(f"Error creating and populating table '{target_table}': {e}")
            return False
    
    def _show_sample_data(self, cursor: sqlite3.Cursor, limit: int = 3, table_name: Optional[str] = None):
        """Show sample data from the table."""
        target_table = table_name if table_name is not None else self.table_name
        try:
            cursor.execute(f"SELECT * FROM {target_table} LIMIT {limit}")
            sample_data = cursor.fetchall()
            
            if sample_data:
                # Get column names
                cursor.execute(f"PRAGMA table_info({target_table})")
                columns = [col[1] for col in cursor.fetchall()]
                
                self._log(f"\nSample data from {target_table}:")
                self._log("-" * 60)
                
                for i, row in enumerate(sample_data, 1):
                    self._log(f"Record {i}:")
                    for col_name, value in zip(columns, row):
                        self._log(f"  {col_name}: {value}")
                    self._log("-" * 30)
                    
        except Exception as e:
            self._log(f"Error showing sample data: {e}")
    
    def get_table_info(self) -> Optional[List[Tuple]]:
        """
        Get table schema information.
        
        Returns:
            Optional[List[Tuple]]: Table info or None if error
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({self.table_name})")
                return cursor.fetchall()
        except Exception as e:
            self._log(f"Error getting table info: {e}")
            return None
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Optional[Tuple[List[str], List[Tuple]]]:
        """
        Execute a SQL query and return results with headers.
        
        Args:
            query (str): SQL query to execute
            params (Optional[Tuple]): Query parameters
            
        Returns:
            Optional[Tuple[List[str], List[Tuple]]]: (headers, results) or None if error
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                headers = [desc[0] for desc in cursor.description] if cursor.description else []
                
                return headers, results
                
        except Exception as e:
            self._log(f"Error executing query: {e}")
            return None
    
    def table_exists(self) -> bool:
        """
        Check if the main table exists.
        
        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (self.table_name,))
                return cursor.fetchone() is not None
        except Exception:
            return False
    
    def get_record_count(self) -> int:
        """
        Get the number of records in the table.
        
        Returns:
            int: Number of records, -1 if error
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                return cursor.fetchone()[0]
        except Exception:
            return -1
