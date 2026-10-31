import os
import duckdb
import pandas as pd
from flask import Flask, render_template, request
from dotenv import load_dotenv


app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()
DB_PATH = os.environ.get("DB_PATH")

def get_daily_data() -> pd.DataFrame:
    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute("""
            SELECT date, kWh_generated, minutes_generating
            FROM daily_data
            ORDER BY date
        """).fetchdf()

def get_five_min_data(date: str) -> pd.DataFrame:
    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute("""
            SELECT time, inverter_generation
            FROM five_min_data
            WHERE date = ?
            ORDER BY time
        """, [date]).fetchdf()

def get_available_dates() -> list[str]:
    with duckdb.connect(DB_PATH, read_only=True) as con:
        rows = con.execute("""
            SELECT DISTINCT date
            FROM five_min_data
            ORDER BY date DESC
        """).fetchdf()
        return [str(d.date()) for d in rows["date"]]

def build_daily_charts(df: pd.DataFrame) -> dict:
    charts = {}

    df["date"] = pd.to_datetime(df["date"])
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

    # Daily kWh bar chart — last 90 days
    recent = df.tail(90).copy()
    charts["daily_bar"] = {
        "data": [{
            "type": "bar",
            "x": recent["date_str"].tolist(),
            "y": recent["kWh_generated"].tolist(),
            "marker": {"color": recent["kWh_generated"].tolist(), "colorscale": "Oranges"},
            "hovertemplate": "Date=%{x}<br>kWh=%{y}<extra></extra>"
        }],
        "layout": {"title": {"text": "Daily Generation — Last 90 Days"},
                   "xaxis": {"title": {"text": "Date"}},
                   "yaxis": {"title": {"text": "kWh"}}}
    }

    # Monthly totals
    df["month_str"] = df["date"].dt.strftime("%Y-%m")
    monthly = df.groupby("month_str", as_index=False)["kWh_generated"].sum()
    charts["monthly_bar"] = {
        "data": [{
            "type": "bar",
            "x": monthly["month_str"].tolist(),
            "y": monthly["kWh_generated"].tolist(),
            "marker": {"color": monthly["kWh_generated"].tolist(), "colorscale": "YlOrRd"},
            "hovertemplate": "Month=%{x}<br>kWh=%{y}<extra></extra>"
        }],
        "layout": {"title": {"text": "Monthly Generation (All Time)"},
                   "xaxis": {"title": {"text": "Month"}},
                   "yaxis": {"title": {"text": "kWh"}}}
    }

    # All-time with 30-day rolling average
    df["rolling_30"] = df["kWh_generated"].rolling(30, min_periods=1).mean()
    charts["rolling"] = {
        "data": [
            {
                "type": "scatter",
                "mode": "lines",
                "x": df["date_str"].tolist(),
                "y": df["kWh_generated"].tolist(),
                "name": "Daily kWh",
                "opacity": 0.35,
                "line": {"color": "#f4a020"}
            },
            {
                "type": "scatter",
                "mode": "lines",
                "x": df["date_str"].tolist(),
                "y": df["rolling_30"].tolist(),
                "name": "30-day avg",
                "line": {"color": "#e05c00", "width": 2}
            }
        ],
        "layout": {"title": {"text": "All-Time Generation with 30-Day Rolling Average"},
                   "xaxis": {"title": {"text": "Date"}},
                   "yaxis": {"title": {"text": "kWh"}}}
    }

    return charts


def build_intraday_chart(df: pd.DataFrame, date: str) -> dict:
    df["time_str"] = df["time"].apply(lambda t: t.strftime("%H:%M:%S"))

    return {
        "data": [{
            "type": "scatter",
            "mode": "lines+markers",
            "x": df["time_str"].tolist(),
            "y": df["inverter_generation"].tolist(),
            "name": "Generation",
            "fill": "tozeroy",
            "fillcolor": "rgba(244,160,32,0.15)",
            "line": {"color": "#f4a020", "width": 2},
            "marker": {"size": 4},
            "hovertemplate": "Time=%{x}<br>Wh=%{y}<extra></extra>"
        }],
        "layout": {
            "title": {"text": f"Intraday Generation — {date}"},
            "xaxis": {"title": {"text": "Time"}},
            "yaxis": {"title": {"text": "Generation (Wh)"}}
        }
    }

def build_stats(df: pd.DataFrame) -> dict:
    today = df.iloc[-1]
    return {
        "total_kwh":     round(df["kWh_generated"].sum(), 1),
        "total_days":    len(df),
        "best_day_kwh":  round(df["kWh_generated"].max(), 2),
        "best_day_date": str(df.loc[df["kWh_generated"].idxmax(), "date"].date()), #type: ignore
        "avg_kwh":       round(df["kWh_generated"].mean(), 2),
        "latest_date":   str(today["date"].date()),
        "latest_kwh":    round(today["kWh_generated"], 2),
        "latest_mins":   int(today["minutes_generating"]),
    }

@app.route("/")
def index():
    daily_df      = get_daily_data()
    stats         = build_stats(daily_df)
    daily_charts  = build_daily_charts(daily_df)
    available     = get_available_dates()

    # Default to most recent date that has 5-min data
    selected_date = request.args.get("date", available[0] if available else None)
    intraday_chart = None
    if selected_date:
        intraday_df    = get_five_min_data(selected_date)
        intraday_chart = build_intraday_chart(intraday_df, selected_date)

    return render_template("index.html",
                           stats=stats,
                           daily_charts=daily_charts,
                           intraday_chart=intraday_chart,
                           available_dates=available,
                           selected_date=selected_date)


def debug():
    df = get_daily_data()
    df["date"] = pd.to_datetime(df["date"])
    recent = df.tail(10).copy()
    return {"dates": recent["date"].dt.strftime("%Y-%m-%d").tolist(),
            "kwh": recent["kWh_generated"].tolist()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)