"""Unit tests for the DataProcessor helper utilities."""

import pandas as pd

from smartink.data_processor import DataProcessor


def test_clean_dataframe_normalizes_columns_and_dates():
    processor = DataProcessor(verbose=False)
    df = pd.DataFrame(
        {
            "Company Name & Details": ["Alpha Ltd"],
            "Listing Date": ["2024-01-15"],
            "Other Column": [1],
        }
    )

    cleaned = processor.clean_dataframe(df)

    # Column names should be normalized to snake_case
    assert "company_name_details" in cleaned.columns
    assert "listing_date" in cleaned.columns

    # Listing date should be converted to datetime64[ns]
    assert str(cleaned["listing_date"].dtype) == "datetime64[ns]"
    # Non-date column stays untouched aside from naming
    assert cleaned["other_column"].iloc[0] == 1
