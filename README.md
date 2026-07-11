# Container Repair Cost Analytics Dashboard

**Interactive Streamlit dashboard analyzing container repair invoicing, billing, and cost variance across ports and repair types.**

[Launch Live App](https://emars-tpc-dashboard-sekiy9jb6pyfgogqozekpn.streamlit.app/)

## Project Overview

Container repair transactions (TPCs) generate invoiced and billed amounts across multiple ports, repair codes, and currencies. This dashboard consolidates that data into a single interactive view so operations teams can spot cost trends, compare ports and repair types, and catch invoice-vs-billed discrepancies without manually cross-referencing spreadsheets.

## Key Features

- **Currency-normalized cost variance** — invoice and billed amounts are converted to USD at transaction-specific exchange rates, then compared to flag over- or under-invoicing
- **Multi-dimensional filtering** — filter by year, TPC status, port code, repair code, and currency simultaneously
- **Trend analysis** — monthly invoice vs. billed trends overall and for the top 5 repair codes by volume
- **Port & repair breakdowns** — bar charts of invoiced amount by port and top repair codes, plus a scatter plot (bubble size = transaction count) comparing invoiced vs. billed by port with a reference y = x line
- **Status & variance views** — TPC status distribution and cost variance grouped by port, repair code, or status

## Tech Stack

Python · Streamlit · Pandas · Plotly (Express + Graph Objects)

## How It's Built

```python
# Core data prep: USD normalization + variance calculation
df["INV_AMOUNT_USD"] = df["INV_AMOUNT"] / df["EXCH_RATE"].replace(0, 1)
df["BILL_AMOUNT_USD"] = df["BILL_AMOUNT"] / df["EXCH_RATE"].replace(0, 1)
df["COST_VARIANCE"] = df["INV_AMOUNT_USD"] - df["BILL_AMOUNT_USD"]
```

The app loads and caches the CSV with `@st.cache_data`, applies sidebar filters reactively, and renders three tabs (Cost Trends, Port & Repair Analysis, Status & Variance) so users can move from a high-level KPI summary down to raw filtered records.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run emars_app.py
```

## What I'd Improve Next

- Move from CSV to a proper database backend for larger datasets
- Add year-over-year comparison view
- Export filtered results to CSV/Excel directly from the dashboard

## Files

- `emars_app.py` — main Streamlit application
- `emars_tpc_shutdown_bkup.csv` / `emars_tpc_shutdown_bkup_trimmed.csv` — source data
- `requirements.txt` — dependencies
