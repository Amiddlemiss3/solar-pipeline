from datetime import date, time
import pandas as pd
import pytest
from pipeline import _filter_daily, _filter_five_min, _prepare_five_min

def test_filter_daily_keeps_only_newer_rows():
    # Create a sample DataFrame with some data
    df = pd.DataFrame({
        "Date": ["2026-10-30", "2026-10-31", "2026-11-01"],
        "kWh_Generated": [5.0, 6.0, 7.0],
        "Minutes_Generating": [400, 410, 420]
    })

    # Call the function and check the result
    result = _filter_daily(df, date(2026, 10, 31), None)
    assert list(result["kWh_Generated"]) == [7.0]

def test_filter_daily_excludes_current_date():
    # Create a sample DataFrame with some data
    df = pd.DataFrame({
        "Date": ["2026-10-30", "2026-10-31", "2026-11-01"],
        "kWh_Generated": [5.0, 6.0, 7.0],
        "Minutes_Generating": [400, 410, 420]
    })

    # Call the function and check the result
    result = _filter_daily(df, date(2026, 10, 31), None)
    assert list(result["Date"]) == [date(2026, 11, 1)]

def test_filter_daily_handles_unparseable_dates():
    # Create a sample DataFrame with some data, including an unparseable date
    df = pd.DataFrame({
        "Date": ["2026-10-30", "not_a_date", "2026-11-01"],
        "kWh_Generated": [5.0, 6.0, 7.0],
        "Minutes_Generating": [400, 410, 420]
    })

    # Call the function and check the result
    result = _filter_daily(df, date(2026, 10, 31), None)
    assert list(result["kWh_Generated"]) == [7.0]

def test_filter_five_min_keeps_only_newer_rows():
    # Create a sample DataFrame with some data
    df = pd.DataFrame({
        "Date": [date(2026, 10, 30), date(2026, 10, 31), date(2026, 11, 1)],
        "Time": [time(12, 0, 0), time(11, 0, 0), time(14, 0, 0)],
        "Inverter_Generation": [5.0, 6.0, 7.0]
    })

    # Call the function and check the result
    result = _filter_five_min(df, date(2026, 10, 31), pd.to_datetime("12:30:00").time())
    assert list(result["Inverter_Generation"]) == [7.0]

def test_prepare_five_min_rejects_invalid_timestamp():
    # Create a sample DataFrame with some data, including an unparseable time
    df = pd.DataFrame({
        "Date/Time": ["2026-02-29 12:00:00", "2026-02-30 12:00:00"],
        "Inverter Generation": [5.0, 6.0]
    })

    # Call the function and check the result
    with pytest.raises(ValueError):
        _prepare_five_min(df)

def test_prepare_filter_five_min_combined():
    # Create a sample DataFrame with some data, including an unparseable time
    df = pd.DataFrame({
        "Date/Time": ["2026-10-30 12:00:00", "2026-10-31 11:00:00", "2026-11-01 14:00:00"],
        "Inverter Generation": [5.0, 6.0, 7.0]
    })

    # Prepare the data
    prepared_df = _prepare_five_min(df)

    # Call the filter function and check the result
    result = _filter_five_min(prepared_df, date(2026, 10, 31), pd.to_datetime("12:30:00").time())
    assert list(result["Inverter_Generation"]) == [7.0]