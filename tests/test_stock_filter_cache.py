"""Tests for the stock filter cache helper."""

from smartink.stock_filter_cache import StockFilterCache


def test_save_and_load_filtered_stocks(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache = StockFilterCache(cache_file=str(cache_path), verbose=False)

    symbols = ["ABC", "XYZ"]
    criteria = {"min_market_cap_cr": 100}

    assert cache.save_filtered_stocks(symbols, criteria, processing_time=0.42)

    loaded = cache.load_filtered_stocks()
    assert loaded is not None

    loaded_symbols, metadata = loaded
    assert loaded_symbols == symbols
    assert metadata["count"] == len(symbols)
    assert metadata["filter_criteria"] == criteria
    assert cache.is_cache_current()

    info = cache.get_cache_info()
    assert info["exists"] is True
    assert info["current"] is True

    assert cache.clear_cache()
    assert cache.load_filtered_stocks() is None
