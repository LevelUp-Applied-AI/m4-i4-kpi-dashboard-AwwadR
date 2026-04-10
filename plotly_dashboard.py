"""
Tier 1 — Interactive Dashboard with Plotly
Amman Digital Market Analytics

Reads data the same way as analysis.py, computes the same KPIs,
and creates an interactive standalone dashboard saved as output/dashboard.html

Usage:
    python plotly_dashboard.py
"""

import os
import subprocess
from io import StringIO

import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from plotly.offline import plot
import plotly.graph_objects as go
from sqlalchemy import create_engine


CONTAINER_NAME = "postgres-m3-int"
DB_NAME = "amman_market"
DB_USER = "postgres"


def connect_db():
    """Create a SQLAlchemy engine connected to the amman_market database."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/amman_market"
    )

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        print("Connected using SQLAlchemy.")
        return engine
    except Exception:
        print("SQLAlchemy connection failed. Using docker exec instead.")
        return None


def _read_table_via_docker(table_name):
    """Read a Postgres table into a DataFrame using docker exec + psql COPY."""
    query = f"COPY (SELECT * FROM {table_name}) TO STDOUT WITH CSV HEADER"

    cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-c",
        query,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read table '{table_name}' via docker.\n{result.stderr}"
        )

    return pd.read_csv(StringIO(result.stdout))


def extract_data(engine):
    """Extract all required tables from the database into DataFrames."""
    tables = ["customers", "products", "orders", "order_items"]
    data = {}

    if engine is not None:
        for table in tables:
            data[table] = pd.read_sql(f"SELECT * FROM {table}", engine)
    else:
        for table in tables:
            data[table] = _read_table_via_docker(table)

    return data


def compute_kpis(data_dict):
    """Compute the same KPIs used in analysis.py."""
    customers = data_dict["customers"].copy()
    products = data_dict["products"].copy()
    orders = data_dict["orders"].copy()
    order_items = data_dict["order_items"].copy()

    # Data cleaning
    orders = orders[orders["status"] != "cancelled"].copy()
    order_items = order_items[order_items["quantity"] <= 100].copy()

    customers["registration_date"] = pd.to_datetime(customers["registration_date"])
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    customers["city"] = customers["city"].fillna("Unknown")

    # Merge tables
    df = order_items.merge(orders, on="order_id", how="inner")
    df = df.merge(products, on="product_id", how="inner")
    df = df.merge(customers, on="customer_id", how="inner")

    # Feature engineering
    df["line_revenue"] = df["quantity"] * df["unit_price"]
    df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
    df["registration_month"] = df["registration_date"].dt.to_period("M").astype(str)

    # Order-level table
    order_totals = (
        df.groupby("order_id", as_index=False)
        .agg(
            customer_id=("customer_id", "first"),
            city=("city", "first"),
            order_date=("order_date", "first"),
            order_month=("order_month", "first"),
            order_revenue=("line_revenue", "sum"),
        )
    )

    # Category contribution per order
    order_category_values = (
        df.groupby(["order_id", "category"], as_index=False)["line_revenue"]
        .sum()
        .rename(columns={"line_revenue": "category_order_value"})
    )

    # KPI 1: Monthly Revenue
    monthly_revenue = (
        df.groupby("order_month", as_index=False)["line_revenue"]
        .sum()
        .sort_values("order_month")
    )

    # KPI 2: Monthly Order Volume
    monthly_order_volume = (
        order_totals.groupby("order_month", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "order_count"})
        .sort_values("order_month")
    )

    # KPI 3: Revenue by City
    revenue_by_city = (
        df.groupby("city", as_index=False)["line_revenue"]
        .sum()
        .sort_values("line_revenue", ascending=False)
    )

    # KPI 4: Average Order Value by Product Category
    avg_order_value_by_category = (
        order_category_values.groupby("category", as_index=False)["category_order_value"]
        .mean()
        .sort_values("category_order_value", ascending=False)
    )

    # KPI 5: Revenue by Registration Cohort
    revenue_by_registration_cohort = (
        df.groupby("registration_month", as_index=False)["line_revenue"]
        .sum()
        .sort_values("registration_month")
    )

    # Extra dataframe for required scatter chart
    city_scatter = (
        df.groupby("city", as_index=False)
        .agg(
            total_revenue=("line_revenue", "sum"),
            avg_line_revenue=("line_revenue", "mean"),
            total_quantity=("quantity", "sum"),
        )
        .sort_values("total_revenue", ascending=False)
    )

    return {
        "clean_df": df,
        "order_totals": order_totals,
        "order_category_values": order_category_values,
        "monthly_revenue": monthly_revenue,
        "monthly_order_volume": monthly_order_volume,
        "revenue_by_city": revenue_by_city,
        "avg_order_value_by_category": avg_order_value_by_category,
        "revenue_by_registration_cohort": revenue_by_registration_cohort,
        "city_scatter": city_scatter,
        "baseline_summary": {
            "total_revenue": round(df["line_revenue"].sum(), 2),
            "total_orders": int(order_totals["order_id"].nunique()),
            "avg_order_value": round(order_totals["order_revenue"].mean(), 2),
            "top_city": revenue_by_city.iloc[0]["city"],
            "top_category": avg_order_value_by_category.iloc[0]["category"],
        },
    }


def create_plotly_dashboard(kpi_results):
    """Create an interactive Plotly dashboard and save it as output/dashboard.html."""
    os.makedirs("output", exist_ok=True)

    monthly_revenue = kpi_results["monthly_revenue"].copy()
    monthly_order_volume = kpi_results["monthly_order_volume"].copy()
    revenue_by_city = kpi_results["revenue_by_city"].copy()
    avg_order_value_by_category = kpi_results["avg_order_value_by_category"].copy()
    cohort = kpi_results["revenue_by_registration_cohort"].copy()
    city_scatter = kpi_results["city_scatter"].copy()
    baseline = kpi_results["baseline_summary"]

    # 1) px.line()
    fig_revenue = px.line(
        monthly_revenue,
        x="order_month",
        y="line_revenue",
        markers=True,
        title="Monthly Revenue Shows the Overall Sales Trend"
    )
    fig_revenue.update_layout(
        xaxis_title="Order Month",
        yaxis_title="Revenue",
        hovermode="x unified"
    )

    # 2) px.line()
    fig_orders = px.line(
        monthly_order_volume,
        x="order_month",
        y="order_count",
        markers=True,
        title="Monthly Order Volume Tracks Demand Over Time"
    )
    fig_orders.update_layout(
        xaxis_title="Order Month",
        yaxis_title="Number of Orders",
        hovermode="x unified"
    )

    # 3) px.bar()
    fig_city = px.bar(
        revenue_by_city,
        x="city",
        y="line_revenue",
        title="Revenue Is Concentrated in the Highest-Performing Cities",
        text_auto=".2s"
    )
    fig_city.update_layout(
        xaxis_title="City",
        yaxis_title="Revenue"
    )

    # 4) px.bar()
    fig_category = px.bar(
        avg_order_value_by_category,
        x="category",
        y="category_order_value",
        title="Average Order Value Differs Across Product Categories",
        text_auto=".2f"
    )
    fig_category.update_layout(
        xaxis_title="Category",
        yaxis_title="Average Order Value"
    )

    # 5) px.scatter() required by tier
    fig_scatter = px.scatter(
        city_scatter,
        x="avg_line_revenue",
        y="total_revenue",
        size="total_quantity",
        hover_name="city",
        text="city",
        title="City Performance: Average Revenue vs Total Revenue"
    )
    fig_scatter.update_layout(
        xaxis_title="Average Revenue per Line Item",
        yaxis_title="Total Revenue"
    )
    fig_scatter.update_traces(textposition="top center")

    # 6) Optional extra KPI chart
    fig_cohort = px.bar(
        cohort,
        x="registration_month",
        y="line_revenue",
        title="Registration Cohorts Contribute Revenue Unevenly",
        text_auto=".2s"
    )
    fig_cohort.update_layout(
        xaxis_title="Registration Month",
        yaxis_title="Revenue"
    )

    # Build one multi-chart dashboard figure
    dashboard = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "Monthly Revenue",
            "Monthly Order Volume",
            "Revenue by City",
            "Average Order Value by Category",
            "City Performance Scatter",
            "Revenue by Registration Cohort",
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
        ],
        vertical_spacing=0.12,
    )

    for trace in fig_revenue.data:
        dashboard.add_trace(trace, row=1, col=1)

    for trace in fig_orders.data:
        dashboard.add_trace(trace, row=1, col=2)

    for trace in fig_city.data:
        dashboard.add_trace(trace, row=2, col=1)

    for trace in fig_category.data:
        dashboard.add_trace(trace, row=2, col=2)

    for trace in fig_scatter.data:
        dashboard.add_trace(trace, row=3, col=1)

    for trace in fig_cohort.data:
        dashboard.add_trace(trace, row=3, col=2)

    dashboard.update_layout(
        title={
            "text": (
                "Amman Digital Market Interactive Dashboard"
                f"<br><sup>Total Revenue: {baseline['total_revenue']} | "
                f"Total Orders: {baseline['total_orders']} | "
                f"Average Order Value: {baseline['avg_order_value']} | "
                f"Top City: {baseline['top_city']} | "
                f"Top Category: {baseline['top_category']}</sup>"
            ),
            "x": 0.5,
            "xanchor": "center"
        },
        height=1400,
        autosize=True,
        showlegend=False,
        margin=dict(l=60, r=60, t=100, b=60)
    )

    dashboard.update_xaxes(title_text="Order Month", row=1, col=1)
    dashboard.update_yaxes(title_text="Revenue", row=1, col=1)

    dashboard.update_xaxes(title_text="Order Month", row=1, col=2)
    dashboard.update_yaxes(title_text="Number of Orders", row=1, col=2)

    dashboard.update_xaxes(title_text="City", row=2, col=1)
    dashboard.update_yaxes(title_text="Revenue", row=2, col=1)

    dashboard.update_xaxes(title_text="Category", row=2, col=2)
    dashboard.update_yaxes(title_text="Average Order Value", row=2, col=2)

    dashboard.update_xaxes(title_text="Average Revenue per Line Item", row=3, col=1)
    dashboard.update_yaxes(title_text="Total Revenue", row=3, col=1)

    dashboard.update_xaxes(title_text="Registration Month", row=3, col=2)
    dashboard.update_yaxes(title_text="Revenue", row=3, col=2)

    # Required export as standalone HTML
    dashboard.write_html(
        "output/dashboard.html",
        include_plotlyjs=True,
        full_html=True
    )

    print("Interactive dashboard saved to output/dashboard.html")


def main():
    """Run the Plotly dashboard pipeline."""
    os.makedirs("output", exist_ok=True)

    engine = connect_db()
    data = extract_data(engine)
    kpi_results = compute_kpis(data)
    create_plotly_dashboard(kpi_results)

    print("\n=== KPI BASELINE SUMMARY ===")
    for key, value in kpi_results["baseline_summary"].items():
        print(f"{key}: {value}")

    print("\nInteractive dashboard saved in output/dashboard.html")


if __name__ == "__main__":
    main()