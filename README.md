# 🚢 Container Repair Cost Analytics Dashboard

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Visualizations-3F4F75?logo=plotly&logoColor=white)

**An interactive dashboard that turns raw container repair invoicing data into a single view for spotting cost overruns across ports and repair types.**

[▶ Live App](https://emars-tpc-dashboard-sekiy9jb6pyfgogqozekpn.streamlit.app/) · [💻 Source Code](https://github.com/MChu2019/emars-tpc-dashboard)

## Problem

Container repair transactions (TPCs) come in with invoiced and billed amounts across dozens of ports, repair codes, and currencies. Spotting where invoiced amounts diverge from billed amounts — or which ports/repair types are driving cost — meant manually cross-referencing spreadsheets. This dashboard consolidates that into filterable, visual views so the discrepancy is visible at a glance instead of buried in rows.

## Technical Decisions

- **Currency normalization at the row level, not in aggregate.** Each transaction has its own exchange rate, so I converted `INV_AMOUNT` and `BILL_AMOUNT` to USD per-row before any aggregation — aggregating first and converting after would have silently distorted totals whenever the currency mix shifted month to month.
- **`@st.cache_data` on the load function**, not on the filtered results — the raw CSV load/parse is the expensive step; filtering is cheap and needs to re-run on every sidebar interaction, so only the load is cached.
- **A y = x reference line on the invoice-vs-billed scatter plot**, so any port sitting above the line is immediately visible as over-invoiced relative to what was billed, without reading axis values.

## One Challenge I Solved

Some transactions had an `EXCH_RATE` of `0` (missing/bad data), which would have caused a division-by-zero when converting to USD. I used `.replace(0, 1)` on the exchange rate column before dividing, so those rows fall back to a 1:1 rate instead of crashing the app or silently producing `inf` values that would have skewed every downstream chart.

```python
df["INV_AMOUNT_USD"] = df["INV_AMOUNT"] / df["EXCH_RATE"].replace(0, 1)
```

## Features

- KPI cards: total records, total invoiced/billed (USD), waiver rate
- Filters: year, TPC status, port code, repair code, currency
- Trend view: monthly invoice vs. billed, plus top-5 repair codes over time
- Port & repair breakdowns: bar charts + invoice-vs-billed scatter (bubble size = transaction count)
- Status & variance breakdown: cost variance grouped by port, repair code, or status

## Setup

```bash
git clone https://github.com/MChu2019/emars-tpc-dashboard.git
cd emars-tpc-dashboard
pip install -r requirements.txt
streamlit run emars_app.py
```

## Files

| File | Purpose |
|---|---|
| `emars_app.py` | Main Streamlit application |
| `emars_tpc_shutdown_bkup.csv` | Source data |
| `emars_tpc_shutdown_bkup_trimmed.csv` | Trimmed dataset for faster local testing |
| `requirements.txt` | Dependencies |

## What I'd Improve Next

- Move from CSV to a database backend for larger datasets
- Add year-over-year comparison view
- Export filtered results directly from the dashboard
