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
        "Date": ["2026-10-30", "2026-10-31", "2026-11-01"],
        "Time": ["12:00:00", "11:00:00", "14:00:00"],
        "Inverter_Generation": [5.0, 6.0, 7.0]
    })

    # Call the function and check the result
    result = _filter_five_min(df, date(2026, 10, 31), pd.to_datetime("12:30:00").time())
    assert list(result["Inverter_Generation"]) == [7.0]

def test_filter_five_min_handles_raw_csv():
    # Create a sample DataFrame with some data, including an unparseable date
    df = pd.DataFrame({
        "Date": ["2026-10-30", "not_a_date", "2026-11-01"],
        "Time": ["12:00:00", "13:00:00", "14:00:00"],
        "Inverter_Generation": [5.0, 6.0, 7.0]
    })

    # Call the function and check the result
    result = _filter_five_min(df, pd.to_datetime("2026-10-31 16:30:11").date(), pd.to_datetime("2026-10-31 16:30:11").time())
    assert list(result["Inverter_Generation"]) == [7.0]

def test_filter_five_min_fails_loud():
    # Create a sample DataFrame with some data, including an unparseable date
    df = pd.DataFrame({
        "Date": ["2026-10-30", "not_a_date"],
        "Time": ["12:00:00", "13:00:00"],
        "Inverter_Generation": [5.0, 6.0]
    })

    # Call the function and check the result
    with pytest.raises(ValueError):
        _filter_five_min(df, date(2026, 10, 31), time(12, 0))

def test_new_filter_five_min_handles_unparseable_time():
    # Create a sample DataFrame with some data, including an unparseable time
    df = pd.DataFrame({
        "Date": ["2026-10-30"],
        "Time": ["12:00:00"],
        "Inverter_Generation": [5.0],
        "Date/Time": "Date/Time	Inverter Generation	\n2026-02-15 16:30:11"
    })

    # Call the function and check the result
    with pytest.raises(ValueError):
        _prepare_five_min(df)