"""Unit tests for breakout analysis helpers."""

import numpy as np
import pandas as pd
import pytest

from smartink.technical_analysis import analyze_breakout_signals


BASE_ROW = {
    "symbol": "BASE",
    "date": pd.Timestamp("2024-01-02"),
    "open": 100.0,
    "high": 101.0,
    "low": 99.0,
    "close": 100.0,
    "volume": 120_000,
    "sma_20": 100.0,
    "sma_50": 98.0,
    "rsi_14": 55.0,
    "prev_open": 99.5,
    "prev_high": 100.0,
    "prev_low": 98.5,
    "prev_close": 99.0,
    "prev_volume": 100_000,
    "prev_sma_20": 99.0,
    "prev_sma_50": 97.5,
    "prev_rsi_14": 52.0,
    "avg_volume_5": 90_000,
    "avg_close_5": 99.5,
    "rolling_high_20": 101.0,
    "rolling_low_20": 95.0,
}


def _make_row(symbol: str, **updates) -> dict:
    row = BASE_ROW.copy()
    row.update({"symbol": symbol})
    row.update(updates)
    return row


@pytest.mark.parametrize(
    ("symbol", "overrides", "expected_status", "expected_signal"),
    [
        (
            "BREAKOUT",
            {"close": 100.5, "high": 101.2, "low": 99.6, "prev_close": 99.0, "prev_sma_20": 99.2},
            "Fresh Breakout Above",
            "Fresh Breakout (Confirmed)",
        ),
        (
            "BREAKDOWN",
            {"close": 99.0, "high": 100.3, "low": 98.4, "prev_close": 100.2, "prev_sma_20": 100.0},
            "Fresh Breakdown Below",
            "Fresh Breakdown (Confirmed)",
        ),
        (
            "RETEST",
            {"close": 100.2, "high": 100.9, "low": 99.4, "prev_close": 100.6, "prev_sma_20": 100.1},
            "Holding Above",
            "Retest & Hold Above",
        ),
        (
            "FAILED",
            {"close": 99.8, "high": 100.4, "low": 99.3, "prev_close": 100.5, "prev_sma_20": 100.2},
            "Holding Below",
            "Failed Breakout - Caution",
        ),
    ],
)
def test_analyze_breakout_signals_classifies_scenarios(symbol, overrides, expected_status, expected_signal):
    df = pd.DataFrame([_make_row(symbol, **overrides)])
    result = analyze_breakout_signals(df, sma_period=20, max_distance=5.0)

    assert result is not None
    assert not result.empty
    row = result.iloc[0]
    assert row["symbol"] == symbol
    assert row["breakout_status"] == expected_status
    assert row["breakout_signal"] == expected_signal
    assert 0 <= row["breakout_confidence"] <= 100


def test_analyze_breakout_signals_handles_missing_sma_gracefully():
    df = pd.DataFrame([_make_row("MISSING", sma_20=np.nan, prev_sma_20=np.nan)])
    result = analyze_breakout_signals(df, sma_period=20)

    assert result is not None
    assert result.empty
