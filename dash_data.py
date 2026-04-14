import os
import json
import subprocess
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine


CONTAINER_NAME = "postgres-m3-int"
DB_NAME = "amman_market"
DB_USER = "postgres"


def connect_db():
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
    tables = ["customers", "products", "orders", "order_items"]
    data = {}

    if engine is not None:
        for table in tables:
            data[table] = pd.read_sql(f"SELECT * FROM {table}", engine)
    else:
        for table in tables:
            data[table] = _read_table_via_docker(table)

    return data


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_clean_df(data_dict):
    customers = data_dict["customers"].copy()
    products = data_dict["products"].copy()
    orders = data_dict["orders"].copy()
    order_items = data_dict["order_items"].copy()

    orders = orders[orders["status"] != "cancelled"].copy()
    order_items = order_items[order_items["quantity"] <= 100].copy()

    customers["registration_date"] = pd.to_datetime(customers["registration_date"])
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    customers["city"] = customers["city"].fillna("Unknown")

    df = order_items.merge(orders, on="order_id", how="inner")
    df = df.merge(products, on="product_id", how="inner")
    df = df.merge(customers, on="customer_id", how="inner")

    df["line_revenue"] = df["quantity"] * df["unit_price"]
    df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
    df["registration_month"] = df["registration_date"].dt.to_period("M").astype(str)

    return df


def filter_clean_df(df, city=None, category=None, start_date=None, end_date=None):
    filtered = df.copy()

    if city and city != "All":
        filtered = filtered[filtered["city"] == city]

    if category and category != "All":
        filtered = filtered[filtered["category"] == category]

    if start_date:
        filtered = filtered[filtered["order_date"] >= pd.to_datetime(start_date)]

    if end_date:
        filtered = filtered[filtered["order_date"] <= pd.to_datetime(end_date)]

    return filtered


def compute_kpis_from_clean_df(df):
    if df.empty:
        return {
            "monthly_revenue": pd.DataFrame(columns=["order_month", "line_revenue"]),
            "monthly_order_volume": pd.DataFrame(columns=["order_month", "order_count"]),
            "revenue_by_city": pd.DataFrame(columns=["city", "line_revenue"]),
            "avg_order_value_by_category": pd.DataFrame(columns=["category", "category_order_value"]),
            "revenue_by_registration_cohort": pd.DataFrame(columns=["registration_month", "line_revenue"]),
            "order_totals": pd.DataFrame(columns=["order_id", "order_revenue"]),
        }

    order_totals = (
        df.groupby("order_id", as_index=False)
        .agg(
            city=("city", "first"),
            order_date=("order_date", "first"),
            order_month=("order_month", "first"),
            order_revenue=("line_revenue", "sum"),
        )
    )

    order_category_values = (
        df.groupby(["order_id", "category"], as_index=False)["line_revenue"]
        .sum()
        .rename(columns={"line_revenue": "category_order_value"})
    )

    monthly_revenue = (
        df.groupby("order_month", as_index=False)["line_revenue"]
        .sum()
        .sort_values("order_month")
    )

    monthly_order_volume = (
        order_totals.groupby("order_month", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "order_count"})
        .sort_values("order_month")
    )

    revenue_by_city = (
        df.groupby("city", as_index=False)["line_revenue"]
        .sum()
        .sort_values("line_revenue", ascending=False)
    )

    avg_order_value_by_category = (
        order_category_values.groupby("category", as_index=False)["category_order_value"]
        .mean()
        .sort_values("category_order_value", ascending=False)
    )

    revenue_by_registration_cohort = (
        df.groupby("registration_month", as_index=False)["line_revenue"]
        .sum()
        .sort_values("registration_month")
    )

    return {
        "monthly_revenue": monthly_revenue,
        "monthly_order_volume": monthly_order_volume,
        "revenue_by_city": revenue_by_city,
        "avg_order_value_by_category": avg_order_value_by_category,
        "revenue_by_registration_cohort": revenue_by_registration_cohort,
        "order_totals": order_totals,
    }


def evaluate_kpi_status(actual, target, warning_ratio):
    warning_threshold = target * warning_ratio
    if actual >= target:
        return "green"
    if actual >= warning_threshold:
        return "yellow"
    return "red"


def build_monitoring_summary_from_clean_df(df, config):
    kpi_results = compute_kpis_from_clean_df(df)

    if kpi_results["monthly_revenue"].empty:
        summary = {
            "monthly_revenue": {"actual": 0.0, "target": config["monthly_revenue"]["target"]},
            "monthly_order_volume": {"actual": 0, "target": config["monthly_order_volume"]["target"]},
            "revenue_by_city": {"actual": 0.0, "target": config["revenue_by_city"]["target"]},
            "avg_order_value_by_category": {
                "actual": 0.0,
                "target": config["avg_order_value_by_category"]["target"],
            },
            "revenue_by_registration_cohort": {
                "actual": 0.0,
                "target": config["revenue_by_registration_cohort"]["target"],
            },
        }
    else:
        summary = {
            "monthly_revenue": {
                "actual": float(kpi_results["monthly_revenue"].iloc[-1]["line_revenue"]),
                "target": config["monthly_revenue"]["target"],
            },
            "monthly_order_volume": {
                "actual": int(kpi_results["monthly_order_volume"].iloc[-1]["order_count"]),
                "target": config["monthly_order_volume"]["target"],
            },
            "revenue_by_city": {
                "actual": float(kpi_results["revenue_by_city"].iloc[0]["line_revenue"]),
                "target": config["revenue_by_city"]["target"],
            },
            "avg_order_value_by_category": {
                "actual": float(kpi_results["avg_order_value_by_category"].iloc[0]["category_order_value"])
                if not kpi_results["avg_order_value_by_category"].empty else 0.0,
                "target": config["avg_order_value_by_category"]["target"],
            },
            "revenue_by_registration_cohort": {
                "actual": float(kpi_results["revenue_by_registration_cohort"].iloc[-1]["line_revenue"]),
                "target": config["revenue_by_registration_cohort"]["target"],
            },
        }

    for kpi_name, values in summary.items():
        values["status"] = evaluate_kpi_status(
            values["actual"],
            values["target"],
            config[kpi_name]["warning_ratio"]
        )

    return summary


def status_to_color(status):
    return {"red": "red", "yellow": "gold", "green": "green"}[status]


def make_gauge_figure(summary, title_text):
    fig = go.Figure()

    gauge_specs = [
        ("Monthly Revenue", summary["monthly_revenue"]),
        ("Order Volume", summary["monthly_order_volume"]),
        ("Top City Revenue", summary["revenue_by_city"]),
        ("Category Avg Order Value", summary["avg_order_value_by_category"]),
        ("Latest Cohort Revenue", summary["revenue_by_registration_cohort"]),
    ]

    positions = [
        {"x": [0.00, 0.48], "y": [0.68, 1.0]},
        {"x": [0.52, 1.00], "y": [0.68, 1.0]},
        {"x": [0.00, 0.48], "y": [0.34, 0.66]},
        {"x": [0.52, 1.00], "y": [0.34, 0.66]},
        {"x": [0.00, 0.48], "y": [0.00, 0.32]},
    ]

    for (label, values), domain in zip(gauge_specs, positions):
        actual = values["actual"]
        target = values["target"]
        status = values["status"]
        upper = max(actual, target, 1) * 1.2

        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=actual,
                delta={"reference": target},
                title={"text": f"{label}<br><span style='font-size:12px'>Status: {status}</span>"},
                domain=domain,
                gauge={
                    "axis": {"range": [0, upper]},
                    "bar": {"color": status_to_color(status)},
                    "steps": [
                        {"range": [0, target * 0.9], "color": "#f8d7da"},
                        {"range": [target * 0.9, target], "color": "#fff3cd"},
                        {"range": [target, upper], "color": "#d4edda"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": target,
                    },
                },
            )
        )

    fig.update_layout(
        title={"text": title_text, "x": 0.5},
        height=900,
        margin=dict(l=40, r=40, t=80, b=40),
    )
    return fig


def build_monthly_revenue_figure(df, title_text):
    kpis = compute_kpis_from_clean_df(df)
    monthly_revenue = kpis["monthly_revenue"].copy()
    fig = px.line(
        monthly_revenue,
        x="order_month",
        y="line_revenue",
        markers=True,
        title=title_text
    )
    fig.update_layout(xaxis_title="Order Month", yaxis_title="Revenue")
    return fig


def build_monthly_order_volume_figure(df, title_text):
    kpis = compute_kpis_from_clean_df(df)
    monthly_orders = kpis["monthly_order_volume"].copy()
    fig = px.line(
        monthly_orders,
        x="order_month",
        y="order_count",
        markers=True,
        title=title_text
    )
    fig.update_layout(xaxis_title="Order Month", yaxis_title="Order Count")
    return fig


def build_cohort_comparison_figure(df, title_text):
    kpis = compute_kpis_from_clean_df(df)
    cohort = kpis["revenue_by_registration_cohort"].copy()
    fig = px.bar(
        cohort,
        x="registration_month",
        y="line_revenue",
        title=title_text
    )
    fig.update_layout(
        xaxis_title="Registration Cohort",
        yaxis_title="Revenue",
        clickmode="event+select"
    )
    return fig


def build_empty_message_figure(title_text, message):
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16}
    )
    fig.update_layout(
        title=title_text,
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=500
    )
    return fig


def build_cohort_drilldown_figure(df, selected_cohort, title_text):
    if not selected_cohort:
        return build_empty_message_figure(
            title_text,
            "Click a cohort bar to see drill-down details."
        )

    working_df = df.copy()
    working_df["registration_month"] = working_df["registration_month"].astype(str)

    selected_cohort = str(pd.to_datetime(selected_cohort).to_period("M"))

    filtered = working_df[working_df["registration_month"] == selected_cohort].copy()

    if filtered.empty:
        return build_empty_message_figure(
            title_text,
            f"No data available for cohort {selected_cohort} under the current city filter."
        )

    by_category = (
        filtered.groupby("category", as_index=False)["line_revenue"]
        .sum()
        .sort_values("line_revenue", ascending=False)
    )

    fig = px.bar(
        by_category,
        x="category",
        y="line_revenue",
        title=title_text
    )
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Revenue",
        height=500
    )
    return fig

ENGINE = connect_db()
RAW_DATA = extract_data(ENGINE)
CLEAN_DF = prepare_clean_df(RAW_DATA)
CONFIG = load_config("config.json")
CITIES = ["All"] + sorted(CLEAN_DF["city"].dropna().unique().tolist())
MIN_DATE = CLEAN_DF["order_date"].min().date()
MAX_DATE = CLEAN_DF["order_date"].max().date()