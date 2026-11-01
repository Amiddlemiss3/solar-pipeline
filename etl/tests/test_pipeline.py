from datetime import date
import pandas as pd
from pipeline import _filter_daily

def test_filter_daily_keeps_only_newer_rows():
    # Create a sample DataFrame with some data
    df = pd.DataFrame({
        "Date": ["2026-10-31", "2026-10-31", "2026-11-01"],
        "kWh_Generated": [5.0, 6.0, 7.0],
        "Minutes_Generating": [400, 410, 420]
    })

    # Call the function and check the result
    result = _filter_daily(df, date(2026, 10, 31), None)
    assert list(result["kWh_Generated"]) == [7.0]
