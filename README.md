# Solar Panel App

An ETL pipeline and dashboard that collects data from a home solar inverter, stores it in DuckDB and visualises generation over time.

![Screenshot](dashboard_screenshot.png)
Screenshot showing current dashboard

## Motivation
Pipeline built to make easy and reliable way to view home solar generation from anywhere for an inverter with no first party application or support.  Additionally, development improved skills in ETL pipelining, local networking, and full end-to-end deployment and maintenance of a project.

## Overview
flowchart TD
    A(Home Inverter) -->| Python ETL script| B(DuckDB)
    B --> C(Flask/Plotly Dashboard)
    C -->|Tailscale| D[Laptop]
    C -->|Tailscale| E[Phone]
    C -->|Tailscale| F[Anywhere!]

* ETL batch script scheduled daily, csv fetched and loaded into DuckDB tables daily_data and five_min_data containing time (date or date and time) and kWh generated during that period (day or 5 min window).  

* Dashboard displays summary cards for basic information including most recent day, number of minutes generating, average daily generation, best day etc.  Overview graphs show previous 90 days or trends over time (monthly and 30-day rolling average).  Graph of daily generation over 5 minute windows viewable with selectible drop down to specify which day to view.  

## Tech Stack
* Python
* SQL
* pandas
* requests
* DuckDB
* Flask
* Plotly
* Tailscale

## Project Structure
solar-pipeline/
├── README.md
├── .gitignore
├── .env.example
├── etl/
│   ├── pipeline.py
│   ├── requirements.txt
│   └── tests/
│       ├── test_pipeline.py
└── dashboard/
    ├── app.py
    ├── requirements.txt
    ├── templates/index.html
    └── static/plotly.min.js

## Roadmap
Upcoming improvements:
* Migrate pipeline to Raspberry Pi
* Containerise with Docker
* CI/CD and testing workflows
* Dashboard improvements
    * Manual update of data from within dashboard
    * Utilise dbt for 
