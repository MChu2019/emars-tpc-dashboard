import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

# =====================================================================================
# 1. APPLICATION SETUP & PAGE CONFIGURATION
# =====================================================================================

st.set_page_config(
    page_title="EMARS TPC Shutdown Analytics",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚢 Container Repair Analytics Portal")
st.caption("Container Repair Cost Analysis | Source: emars_tpc_shutdown_bkup.csv")
st.markdown("---")

# =====================================================================================
# 2. DATA LOADING & CACHING LAYER (CSV-based, replaces BigQuery)
# =====================================================================================

@st.cache_data
def load_data(filepath: str) -> pd.DataFrame:
    """
    Loads and preprocesses the EMARS TPC shutdown CSV.
    Replaces the original BigQuery engine with a local CSV read.
    """
    df = pd.read_csv(filepath)

    # Parse date columns — handle mixed formats gracefully
    for col in ["CREATE_DATE", "MODIFY_DATE"]:
        df[col] = pd.to_datetime(df[col], dayfirst=False, errors="coerce")

    # Derive useful time columns from CREATE_DATE
    df["YEAR_MONTH"] = df["CREATE_DATE"].dt.to_period("M").dt.to_timestamp()
    df["YEAR"] = df["CREATE_DATE"].dt.year

    # Numeric cleanup — fill NaN monetary fields with 0 for aggregation
    for col in ["INV_AMOUNT", "BILL_AMOUNT", "WAIVER_AMOUNT", "COLLECT_AMOUNT", "REFUND_AMOUNT"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Compute USD-normalised invoice amount using exchange rate
    df["INV_AMOUNT_USD"] = df["INV_AMOUNT"] / df["EXCH_RATE"].replace(0, 1)
    df["BILL_AMOUNT_USD"] = df["BILL_AMOUNT"] / df["EXCH_RATE"].replace(0, 1)

    # Variance: difference between invoiced and billed (positive = over-invoiced)
    df["COST_VARIANCE"] = df["INV_AMOUNT_USD"] - df["BILL_AMOUNT_USD"]

    return df


# Resolve CSV path — supports running from any working directory
CSV_PATH = os.path.join(os.path.dirname(__file__), "emars_tpc_shutdown_bkup.csv")

with st.spinner("Loading EMARS TPC data from CSV..."):
    try:
        master_df = load_data(CSV_PATH)
    except FileNotFoundError:
        st.error(
            f"Click to Load the Data" 
        )
        st.stop()

# =====================================================================================
# 3. SIDEBAR NAVIGATION & FILTERS
# =====================================================================================
st.sidebar.header("🎛️ Operational Parameters")

# --- Year filter (replaces the BigQuery time-window partition control) ---
available_years = sorted(master_df["YEAR"].dropna().unique().astype(int))
selected_years = st.sidebar.multiselect(
    "Transaction Year(s)",
    options=available_years,
    default=available_years,
    help="Filter records by the year the TPC was created"
)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Dimensional Filters")

# TPC Status filter
all_statuses = sorted(master_df["TPC_STATUS"].dropna().unique())
selected_statuses = st.sidebar.multiselect("TPC Status", all_statuses, default=all_statuses)

# Port Code filter
all_ports = sorted(master_df["PORT_CODE"].dropna().unique())
selected_ports = st.sidebar.multiselect("Port Code", all_ports, default=all_ports[:10])

# Repair Code filter
all_repairs = sorted(master_df["REPAIR_CODE"].dropna().unique())
selected_repairs = st.sidebar.multiselect("Repair Code", all_repairs, default=all_repairs)

# Currency filter
all_currencies = sorted(master_df["CURRENCY_CODE"].dropna().unique())
selected_currencies = st.sidebar.multiselect("Currency", all_currencies, default=all_currencies)

# Apply all filters
filtered_df = master_df[
    (master_df["YEAR"].isin(selected_years)) &
    (master_df["TPC_STATUS"].isin(selected_statuses)) &
    (master_df["PORT_CODE"].isin(selected_ports)) &
    (master_df["REPAIR_CODE"].isin(selected_repairs)) &
    (master_df["CURRENCY_CODE"].isin(selected_currencies))
]

# =====================================================================================
# 4. KPI FLASH-CARDS
# =====================================================================================
st.subheader("📊 Key Performance Metrics")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

if not filtered_df.empty:
    with kpi1:
        st.metric("Total TPC Records", f"{len(filtered_df):,}")
    with kpi2:
        st.metric("Total Invoice Amount (USD)", f"${filtered_df['INV_AMOUNT_USD'].sum():,.0f}")
    with kpi3:
        st.metric("Total Billed Amount (USD)", f"${filtered_df['BILL_AMOUNT_USD'].sum():,.0f}")
    with kpi4:
        waiver_pct = (
            filtered_df["WAIVER_AMOUNT"].sum() / filtered_df["INV_AMOUNT"].sum() * 100
            if filtered_df["INV_AMOUNT"].sum() > 0 else 0
        )
        st.metric("Waiver Rate", f"{waiver_pct:.1f}%")
else:
    st.warning("No records match the selected filters. Adjust the sidebar filters.")

st.markdown("---")

# =====================================================================================
# 5. MULTI-TAB ANALYTICS INTERFACE
# =====================================================================================
tab1, tab2, tab3 = st.tabs([
    "📈 Cost Trends Over Time",
    "🌍 Port & Repair Analysis",
    "⚙️ Status & Variance Breakdown"
])

# ---- TAB 1: COST TRENDS OVER TIME ----
with tab1:
    st.subheader("Monthly Invoice & Billing Trends (USD-normalised)")

    if not filtered_df.empty:
        trend_df = (
            filtered_df.groupby("YEAR_MONTH")[["INV_AMOUNT_USD", "BILL_AMOUNT_USD"]]
            .sum()
            .reset_index()
            .rename(columns={
                "YEAR_MONTH": "Month",
                "INV_AMOUNT_USD": "Total Invoiced (USD)",
                "BILL_AMOUNT_USD": "Total Billed (USD)"
            })
        )

        fig_trend = px.line(
            trend_df,
            x="Month",
            y=["Total Invoiced (USD)", "Total Billed (USD)"],
            markers=True,
            title="Monthly Invoice vs. Billed Amounts Over Time",
            labels={"value": "Amount (USD)", "variable": "Metric"}
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("---")
        st.subheader("Repair Code Cost Trend Over Time (Top 5 by Volume)")

        top_repairs = (
            filtered_df.groupby("REPAIR_CODE")["INV_AMOUNT_USD"]
            .sum()
            .nlargest(5)
            .index.tolist()
        )
        repair_trend_df = (
            filtered_df[filtered_df["REPAIR_CODE"].isin(top_repairs)]
            .groupby(["YEAR_MONTH", "REPAIR_CODE"])["INV_AMOUNT_USD"]
            .sum()
            .reset_index()
        )
        fig_repair_trend = px.line(
            repair_trend_df,
            x="YEAR_MONTH",
            y="INV_AMOUNT_USD",
            color="REPAIR_CODE",
            markers=True,
            title="Top 5 Repair Codes — Monthly Invoice Amount (USD)",
            labels={"YEAR_MONTH": "Month", "INV_AMOUNT_USD": "Invoiced Amount (USD)"}
        )
        st.plotly_chart(fig_repair_trend, use_container_width=True)
    else:
        st.caption("No temporal data to display.")

# ---- TAB 2: PORT & REPAIR ANALYSIS ----
with tab2:
    st.subheader("Invoice Amount by Port Code")

    if not filtered_df.empty:
        col_left, col_right = st.columns(2)

        with col_left:
            port_summary = (
                filtered_df.groupby("PORT_CODE")["INV_AMOUNT_USD"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig_port = px.bar(
                port_summary,
                x="PORT_CODE",
                y="INV_AMOUNT_USD",
                text_auto=".2s",
                color="INV_AMOUNT_USD",
                color_continuous_scale="Blues",
                title="Total Invoiced Amount (USD) by Port",
                labels={"PORT_CODE": "Port Code", "INV_AMOUNT_USD": "Invoiced (USD)"}
            )
            fig_port.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_port, use_container_width=True)

        with col_right:
            repair_summary = (
                filtered_df.groupby("REPAIR_CODE")["INV_AMOUNT_USD"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
                .reset_index()
            )
            fig_repair = px.bar(
                repair_summary,
                x="REPAIR_CODE",
                y="INV_AMOUNT_USD",
                text_auto=".2s",
                color="INV_AMOUNT_USD",
                color_continuous_scale="Oranges",
                title="Top 15 Repair Codes by Total Invoice Amount (USD)",
                labels={"REPAIR_CODE": "Repair Code", "INV_AMOUNT_USD": "Invoiced (USD)"}
            )
            fig_repair.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_repair, use_container_width=True)

        st.markdown("---")
        st.subheader("Invoice vs. Billed by Port (Scatter — bubble = record count)")

        port_scatter = filtered_df.groupby("PORT_CODE").agg(
            INV=("INV_AMOUNT_USD", "sum"),
            BILL=("BILL_AMOUNT_USD", "sum"),
            COUNT=("TPC_NO", "count")
        ).reset_index()

        fig_scatter = px.scatter(
            port_scatter,
            x="INV",
            y="BILL",
            size="COUNT",
            color="PORT_CODE",
            hover_name="PORT_CODE",
            title="Total Invoiced vs. Billed by Port (bubble size = # of TPCs)",
            labels={"INV": "Total Invoiced (USD)", "BILL": "Total Billed (USD)"}
        )
        # Add perfect billing line (y=x) for reference
        max_val = max(port_scatter["INV"].max(), port_scatter["BILL"].max()) * 1.05
        fig_scatter.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines",
            line=dict(dash="dash", color="grey"),
            name="Invoice = Bill (reference)"
        ))
        st.plotly_chart(fig_scatter, use_container_width=True)

    else:
        st.caption("No port data to display.")

# ---- TAB 3: STATUS & VARIANCE BREAKDOWN ----
with tab3:
    st.subheader("TPC Status Distribution")

    if not filtered_df.empty:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            status_counts = filtered_df["TPC_STATUS"].value_counts().reset_index()
            status_counts.columns = ["TPC_STATUS", "Count"]
            fig_status = px.pie(
                status_counts,
                names="TPC_STATUS",
                values="Count",
                title="TPC Records by Status",
                hole=0.4
            )
            st.plotly_chart(fig_status, use_container_width=True)

        with col_s2:
            status_cost = (
                filtered_df.groupby("TPC_STATUS")["INV_AMOUNT_USD"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig_status_cost = px.bar(
                status_cost,
                x="TPC_STATUS",
                y="INV_AMOUNT_USD",
                color="TPC_STATUS",
                text_auto=".2s",
                title="Total Invoice Amount (USD) by TPC Status",
                labels={"INV_AMOUNT_USD": "Invoiced (USD)", "TPC_STATUS": "Status"}
            )
            fig_status_cost.update_layout(showlegend=False)
            st.plotly_chart(fig_status_cost, use_container_width=True)

        st.markdown("---")
        st.subheader("Cost Variance (Invoice − Billed, USD-normalised)")
        st.caption("Positive = over-invoiced vs. billed. Negative = billed exceeded invoice (rare).")

        variance_view = st.radio(
            "Group variance by:",
            ["Port Code", "Repair Code", "TPC Status"],
            horizontal=True
        )

        group_map = {
            "Port Code": "PORT_CODE",
            "Repair Code": "REPAIR_CODE",
            "TPC Status": "TPC_STATUS"
        }
        group_col = group_map[variance_view]

        variance_df = (
            filtered_df.groupby(group_col)["COST_VARIANCE"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        variance_df.columns = [variance_view, "Cost Variance (USD)"]

        fig_var = px.bar(
            variance_df,
            x=variance_view,
            y="Cost Variance (USD)",
            color="Cost Variance (USD)",
            color_continuous_scale="RdYlGn_r",
            text_auto=".2s",
            title=f"Total Cost Variance grouped by {variance_view}"
        )
        fig_var.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_var, use_container_width=True)

    else:
        st.warning("No data available for the selected filters.")

# =====================================================================================
# 6. RAW DATA INSPECTION
# =====================================================================================
st.markdown("---")
if st.checkbox("🔍 Show raw filtered data"):
    st.markdown("### Raw TPC Records")
    st.dataframe(filtered_df.reset_index(drop=True))
