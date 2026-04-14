import os
import json
import subprocess
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


def compute_kpis_from_clean_df(df):
    if df.empty:
        return {
            "clean_df": df,
            "order_totals": pd.DataFrame(
                columns=["order_id", "customer_id", "city", "order_date", "order_month", "order_revenue"]
            ),
            "monthly_revenue": pd.DataFrame(columns=["order_month", "line_revenue"]),
            "monthly_order_volume": pd.DataFrame(columns=["order_month", "order_count"]),
            "revenue_by_city": pd.DataFrame(columns=["city", "line_revenue"]),
            "avg_order_value_by_category": pd.DataFrame(columns=["category", "category_order_value"]),
            "revenue_by_registration_cohort": pd.DataFrame(columns=["registration_month", "line_revenue"]),
        }

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
        "clean_df": df,
        "order_totals": order_totals,
        "monthly_revenue": monthly_revenue,
        "monthly_order_volume": monthly_order_volume,
        "revenue_by_city": revenue_by_city,
        "avg_order_value_by_category": avg_order_value_by_category,
        "revenue_by_registration_cohort": revenue_by_registration_cohort,
    }


def compute_kpis(data_dict):
    df = prepare_clean_df(data_dict)
    return compute_kpis_from_clean_df(df)


def filter_clean_df(df, city=None, category=None, start_date=None, end_date=None):
    filtered = df.copy()

    if city is not None and city != "All":
        filtered = filtered[filtered["city"] == city]

    if category is not None and category != "All":
        filtered = filtered[filtered["category"] == category]

    if start_date is not None:
        filtered = filtered[filtered["order_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        filtered = filtered[filtered["order_date"] <= pd.to_datetime(end_date)]

    return filtered


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_kpi_status(actual, target, warning_ratio):
    warning_threshold = target * warning_ratio

    if actual >= target:
        return "green"
    elif actual >= warning_threshold:
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
                "target": config["avg_order_value_by_category"]["target"]
            },
            "revenue_by_registration_cohort": {
                "actual": 0.0,
                "target": config["revenue_by_registration_cohort"]["target"]
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


def build_monitoring_summary(kpi_results, config):
    return build_monitoring_summary_from_clean_df(kpi_results["clean_df"], config)


def status_to_color(status):
    mapping = {"red": "red", "yellow": "gold", "green": "green"}
    return mapping[status]


def make_indicator_figure(summary, title_text):
    fig = make_subplots(
        rows=3,
        cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, None],
        ],
        subplot_titles=(
            "Monthly Revenue",
            "Order Volume",
            "Top City Revenue",
            "Category Avg Order Value",
            "Latest Cohort Revenue",
        ),
        vertical_spacing=0.18
    )

    for annotation in fig["layout"]["annotations"]:
        annotation["y"] += 0.03

    kpis = [
        ("monthly_revenue", 1, 1),
        ("monthly_order_volume", 1, 2),
        ("revenue_by_city", 2, 1),
        ("avg_order_value_by_category", 2, 2),
        ("revenue_by_registration_cohort", 3, 1),
    ]

    for kpi_name, row, col in kpis:
        actual = summary[kpi_name]["actual"]
        target = summary[kpi_name]["target"]
        status = summary[kpi_name]["status"]

        upper_bound = max(actual, target, 1) * 1.2

        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=actual,
                delta={"reference": target},
                gauge={
                    "axis": {"range": [0, upper_bound]},
                    "bar": {"color": status_to_color(status)},
                    "steps": [
                        {"range": [0, target * 0.9], "color": "#f8d7da"},
                        {"range": [target * 0.9, target], "color": "#fff3cd"},
                        {"range": [target, upper_bound], "color": "#d4edda"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": target,
                    },
                },
            ),
            row=row,
            col=col
        )

    fig.update_layout(
        title={
            "text": title_text,
            "x": 0.5,
            "xanchor": "center",
            "y": 0.98
        },
        height=1000,
        showlegend=False,
        margin=dict(l=60, r=60, t=160, b=60)
    )

    return fig


def build_city_summaries(clean_df, config):
    cities = ["All"] + sorted(clean_df["city"].dropna().unique().tolist())
    summaries = {}

    for city in cities:
        filtered_df = filter_clean_df(clean_df, city=city)
        summaries[city] = build_monitoring_summary_from_clean_df(filtered_df, config)

    return summaries


def build_category_summaries(clean_df, config):
    categories = ["All"] + sorted(clean_df["category"].dropna().unique().tolist())
    summaries = {}

    for category in categories:
        filtered_df = filter_clean_df(clean_df, category=category)
        summaries[category] = build_monitoring_summary_from_clean_df(filtered_df, config)

    return summaries


def build_date_range_summaries(clean_df, config):
    min_date = clean_df["order_date"].min()
    max_date = clean_df["order_date"].max()
    mid_date = min_date + (max_date - min_date) / 2

    date_ranges = {
        "All": (None, None),
        "First Half": (None, mid_date),
        "Second Half": (mid_date, None),
    }

    summaries = {}
    for label, (start_date, end_date) in date_ranges.items():
        filtered_df = filter_clean_df(
            clean_df,
            start_date=start_date,
            end_date=end_date
        )
        summaries[label] = build_monitoring_summary_from_clean_df(filtered_df, config)

    return summaries


def create_dropdown_figure(summaries, section_title):
    first_key = list(summaries.keys())[0]
    first_summary = summaries[first_key]

    fig = make_indicator_figure(
        first_summary,
        f"{section_title} — {first_key}"
    )

    buttons = []
    trace_order = [
        "monthly_revenue",
        "monthly_order_volume",
        "revenue_by_city",
        "avg_order_value_by_category",
        "revenue_by_registration_cohort",
    ]

    for option_name, summary in summaries.items():
        new_values = [summary[k]["actual"] for k in trace_order]
        new_delta_refs = [summary[k]["target"] for k in trace_order]
        new_bar_colors = [status_to_color(summary[k]["status"]) for k in trace_order]
        new_axis_ranges = [
            [0, max(summary[k]["actual"], summary[k]["target"], 1) * 1.2]
            for k in trace_order
        ]

        buttons.append(
            dict(
                label=option_name,
                method="update",
                args=[
                    {
                        "value": new_values,
                        "delta.reference": new_delta_refs,
                        "gauge.bar.color": new_bar_colors,
                        "gauge.axis.range": new_axis_ranges,
                    },
                    {
                        "title.text": f"{section_title} — {option_name}"
                    },
                ],
            )
        )

    fig.update_layout(
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.15,
                yanchor="top"
            )
        ]
    )

    return fig


def create_monitor_dashboard_with_filters(clean_df, config):
    os.makedirs("output", exist_ok=True)

    city_summaries = build_city_summaries(clean_df, config)
    category_summaries = build_category_summaries(clean_df, config)
    date_range_summaries = build_date_range_summaries(clean_df, config)

    fig_city = create_dropdown_figure(city_summaries, "City Filter Monitoring")
    fig_category = create_dropdown_figure(category_summaries, "Category Filter Monitoring")
    fig_date = create_dropdown_figure(date_range_summaries, "Date Range Filter Monitoring")

    city_html = fig_city.to_html(full_html=False, include_plotlyjs="cdn")
    category_html = fig_category.to_html(full_html=False, include_plotlyjs=False)
    date_html = fig_date.to_html(full_html=False, include_plotlyjs=False)

    dashboard_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>KPI Monitoring Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background-color: #f8f9fa;
            }}
            h1 {{
                text-align: center;
            }}
            .section {{
                background: white;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
        </style>
    </head>
    <body>
        <h1>KPI Monitoring Dashboard</h1>

        <div class="section">
            {city_html}
        </div>

        <div class="section">
            {category_html}
        </div>

        <div class="section">
            {date_html}
        </div>
    </body>
    </html>
    """

    with open("output/kpi_monitor.html", "w", encoding="utf-8") as f:
        f.write(dashboard_html)

    print("KPI monitoring dashboard saved to output/kpi_monitor.html")


def main():
    engine = connect_db()
    data = extract_data(engine)
    kpi_results = compute_kpis(data)
    config = load_config("config.json")

    summary = build_monitoring_summary(kpi_results, config)
    create_monitor_dashboard_with_filters(kpi_results["clean_df"], config)

    print("\n=== KPI MONITOR SUMMARY ===")
    for kpi_name, values in summary.items():
        print(
            f"{kpi_name}: actual={values['actual']}, "
            f"target={values['target']}, status={values['status']}"
        )


if __name__ == "__main__":
    main()