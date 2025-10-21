"""Smoke tests ensuring the SmartInk package structure is importable."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "smartink",
        "smartink.config",
        "smartink.data_processor",
        "smartink.database_manager",
        "smartink.optimized_stock_filter",
        "smartink.stock_data_fetcher",
        "smartink.stock_data_manager",
        "smartink.stock_filter",
        "smartink.stock_filter_cache",
        "smartink.technical_analysis",
        "smartink.utils",
    ],
)
def test_import_module(module_name):
    """Each core module should be importable without side effects."""
    module = importlib.import_module(module_name)
    assert module is not None
