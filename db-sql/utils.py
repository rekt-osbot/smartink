"""
Shared utility functions for the NSE stocks database application.
This module contains common functions used across multiple modules to eliminate code duplication.
"""

import re
import os
import platform
from pathlib import Path


def normalize_column_name(col_name):
    """
    Convert column name to snake_case format.
    
    This function:
    - Strips whitespace
    - Replaces spaces and special characters with underscores
    - Converts to lowercase
    - Removes multiple consecutive underscores
    - Removes leading/trailing underscores
    
    Args:
        col_name (str): The original column name
        
    Returns:
        str: The normalized column name in snake_case format
    """
    # Strip whitespace
    col_name = col_name.strip()
    # Replace spaces and special characters with underscores
    col_name = re.sub(r'[\s\-\.\&]+', '_', col_name)
    # Convert to lowercase
    col_name = col_name.lower()
    # Remove multiple underscores
    col_name = re.sub(r'_+', '_', col_name)
    # Remove leading/trailing underscores
    col_name = col_name.strip('_')
    return col_name


def clear_screen():
    """Clear the console screen based on the operating system."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


def get_project_root():
    """
    Get the project root directory.
    
    Returns:
        Path: The path to the project root directory
    """
    return Path(__file__).parent


def ensure_file_exists(file_path, description="File"):
    """
    Check if a file exists and raise a descriptive error if it doesn't.
    
    Args:
        file_path (str or Path): Path to the file to check
        description (str): Description of the file for error messages
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path.absolute()}")


def print_section_header(title, width=60):
    """
    Print a formatted section header.
    
    Args:
        title (str): The title to display
        width (int): Width of the header line
    """
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print()


def print_step(step_number, description):
    """
    Print a formatted step description.
    
    Args:
        step_number (int): The step number
        description (str): Description of the step
    """
    print(f"\nStep {step_number}: {description}")
    print("-" * (len(description) + 10))
