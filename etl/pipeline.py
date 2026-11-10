import os
import duckdb
import pandas as pd
import requests
import time as time_module
from io import StringIO
import logging
from datetime import date, time
from typing import Optional, cast
from dotenv import load_dotenv

def main():
    """Main function to run the ETL pipeline."""
    # Load environment variables from .env file
    load_dotenv()
    inverter_ip = os.environ["INVERTER_IP"]
    pipeline_log = os.environ["PIPELINE_LOG_PATH"]
    db_path = os.environ["DB_PATH"]

    # Set up logging
    logging.basicConfig(
        filename=pipeline_log,
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=logging.INFO,
    )

    # Define URLs for fetching data from inverter
    daily_url = f"http://{inverter_ip}/log_daily.csv"
    five_min_url = f"http://{inverter_ip}/log_5min.csv"

    # Start the update process
    logging.info("Starting solar panel data update script.")
    update_solar_panel_db(daily_url, "daily_data", db_path)
    time_module.sleep(3)  # brief pause to avoid overloading the inverter's web server
    update_solar_panel_db(five_min_url, "five_min_data", db_path)

def _prepare_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Rename and return columns for the daily_data table."""
    return df.rename(columns={
        df.columns[0]: 'Date',
        df.columns[1]: 'kWh_Generated',
        df.columns[2]: 'Minutes_Generating',
    })


def _prepare_five_min(df: pd.DataFrame) -> pd.DataFrame:
    """Split Date/Time column and rename for the five_min_data table."""
    df = df.copy()
    # test new datetime columns for parseability, and raise errors for any that fail to parse
    df['Timestamp'] = pd.to_datetime(df['Date/Time'], errors='raise', format="%Y-%m-%d %H:%M:%S")
    df['Date'] = df['Timestamp'].dt.date
    df['Time'] = df['Timestamp'].dt.time
    df = df[['Date', 'Time', 'Inverter Generation']]
    return df.rename(columns={
        df.columns[0]: 'Date',
        df.columns[1]: 'Time',
        df.columns[2]: 'Inverter_Generation',
    })


def _filter_daily(df: pd.DataFrame, ref_date: Optional[date], _ref_time: Optional[time]) -> pd.DataFrame:
    """Return only rows with Date strictly after ref_date."""
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
    return df[df['Date'] > ref_date]


def _filter_five_min(df: pd.DataFrame, ref_date: Optional[date], ref_time: Optional[time]) -> pd.DataFrame:
    """Return only rows with Date/Time strictly after ref_date/ref_time."""
    df = df.copy()
    mask: pd.Series = (df['Date'] > ref_date) | ((df['Date'] == ref_date) & (df['Time'] > ref_time))
    return df[mask]


# TABLE_CONFIG is the single source of truth for everything that differs between tables.
# To add a third table in future, add one entry here — no other code needs to change.
TABLE_CONFIG: dict[str, dict[str, object]] = {
    "daily_data": {
        "prepare":     _prepare_daily,
        "filter":      _filter_daily,
        "latest_sql":  "SELECT date AS Date FROM daily_data ORDER BY Date DESC LIMIT 1;",
        "date_col":    "Date",
        "time_col":    None,
        "insert_sql":  """
                         INSERT INTO daily_data (date, kWh_Generated, Minutes_Generating)
                         SELECT * FROM daily_upload ORDER BY Date ASC;
                       """,
        "empty_error": "daily_data table returned no rows — cannot determine most recent date.",
    },
    "five_min_data": {
        "prepare":     _prepare_five_min,
        "filter":      _filter_five_min,
        "latest_sql":  "SELECT Date AS Date, Time AS Time FROM five_min_data ORDER BY Date DESC, Time DESC LIMIT 1;",
        "date_col":    "Date",
        "time_col":    "Time",
        "insert_sql":  """
                         INSERT INTO five_min_data (date, time, inverter_generation)
                         SELECT * FROM daily_upload ORDER BY Date ASC, Time ASC;
                       """,
        "empty_error": "five_min_data table returned no rows — cannot determine most recent date/time.",
    },
}


def update_solar_panel_db(url: str, table_name: str, db_path: str) -> None:
    if table_name not in TABLE_CONFIG:
        raise ValueError(f"Unknown table_name '{table_name}'. Valid options: {list(TABLE_CONFIG)}")

    config = TABLE_CONFIG[table_name]
    logging.info(f"Fetching data from {url} for table {table_name}.")

    # --- Fetch (with retry) ---
    max_retries = 3
    retry_delay_seconds = 5
    data_df: Optional[pd.DataFrame] = None

    for attempt in range(1, max_retries + 1):
        try:
            with requests.get(url, timeout=30) as r:
                r.raise_for_status()
                content = r.content
                try:
                    text = content.decode("utf-8")
                except UnicodeDecodeError:
                    text = content.decode("utf-16")
                data_df = pd.read_csv(StringIO(text), sep="\t", header=1)
                data_df.columns = [c.replace('\ufeff', '').strip() for c in data_df.columns]
            logging.info(f"Successfully fetched data from {url} on attempt {attempt}.")
            break
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt}/{max_retries} failed fetching {url}: {e}")
            if attempt < max_retries:
                time_module.sleep(retry_delay_seconds)
            else:
                logging.error(f"All {max_retries} attempts failed fetching {url}: {e}")
                raise

    assert data_df is not None  # guaranteed by the raise above if all attempts failed

    # --- Clean ---
    last_col = data_df.columns[-1]
    if data_df[last_col].isna().all() or (data_df[last_col].astype(str).str.strip() == '').all():
        data_df = data_df.iloc[:, :-1].copy()

    if data_df.empty:
        raise ValueError(f"No data retrieved from {url} for {table_name}.")

    # --- Prepare (rename/reshape columns) ---
    prepared_df = config["prepare"](data_df) #type: ignore

    # --- Connect and insert ---
    logging.info("Connecting to DuckDB database.")
    with duckdb.connect(db_path) as con:
        logging.info("Successfully connected to DuckDB database.")

        # Get the most recent date (and time, if applicable) already in the DB
        most_recent = con.sql(config["latest_sql"]).to_df() #type: ignore
        if most_recent.empty:
            logging.error(config["empty_error"])
            raise RuntimeError(config["empty_error"])

        ref_date: Optional[date] = cast(date, pd.to_datetime(most_recent[config["date_col"]].iloc[0]).date()) #type: ignore
        ref_time: Optional[time] = None
        if config["time_col"]:
            ref_time = cast(time, pd.to_datetime(most_recent[config["time_col"]].iloc[0], format="%H:%M:%S").time()) #type: ignore

        logging.info(f"Most recent record in database: {ref_date} {ref_time or ''}. Filtering incoming data.")

        # --- Filter to only new rows ---
        try:
            daily_upload = config["filter"](prepared_df, ref_date, ref_time) #type: ignore
            logging.info(f"Filtered to {len(daily_upload)} new rows for {table_name}.") #type: ignore
        except Exception as e:
            logging.error(f"Error filtering data for {table_name}: {e}")
            raise

        # --- Insert ---
        logging.info(f"Inserting {len(daily_upload)} new rows into {table_name}.") #type: ignore
        try:
            con.sql(config["insert_sql"]) #type: ignore
            logging.info(f"Successfully inserted new rows into {table_name}.")
        except duckdb.Error as e:
            logging.error(f"Error inserting into {table_name}: {e}")
            raise

    logging.info(f"Finished update for {table_name}.")


if __name__ == "__main__":
    main()
