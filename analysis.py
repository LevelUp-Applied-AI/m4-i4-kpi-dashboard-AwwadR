"""Integration 4 — KPI Dashboard: Amman Digital Market Analytics

Extract data from PostgreSQL, compute KPIs, run statistical tests,
and create visualizations for the executive summary.

Usage:
    python analysis.py
"""

import os
import subprocess
from io import StringIO

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sqlalchemy import create_engine


CONTAINER_NAME = "postgres-m3-int"
DB_NAME = "amman_market"
DB_USER = "postgres"


def connect_db():
    """Create a SQLAlchemy engine connected to the amman_market database.

    Returns:
        engine: SQLAlchemy engine instance, or None if connection fails.

    Notes:
        Use DATABASE_URL environment variable if set, otherwise default to:
        postgresql+psycopg://postgres:postgres@127.0.0.1:5432/amman_market
    """
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
    """Extract all required tables from the database into DataFrames.

    Args:
        engine: SQLAlchemy engine connected to amman_market, or None

    Returns:
        dict: mapping of table names to DataFrames
    """
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
    """Compute the 5 KPIs defined in kpi_framework.md.

    Args:
        data_dict: dict of DataFrames from extract_data()

    Returns:
        dict: mapping of KPI names to their computed values
    """
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

    return {
        "clean_df": df,
        "order_totals": order_totals,
        "order_category_values": order_category_values,
        "monthly_revenue": monthly_revenue,
        "monthly_order_volume": monthly_order_volume,
        "revenue_by_city": revenue_by_city,
        "avg_order_value_by_category": avg_order_value_by_category,
        "revenue_by_registration_cohort": revenue_by_registration_cohort,
        "baseline_summary": {
            "total_revenue": round(df["line_revenue"].sum(), 2),
            "total_orders": int(order_totals["order_id"].nunique()),
            "avg_order_value": round(order_totals["order_revenue"].mean(), 2),
            "top_city": revenue_by_city.iloc[0]["city"],
            "top_category": avg_order_value_by_category.iloc[0]["category"],
        },
    }


def run_statistical_tests(data_dict):
    """Run hypothesis tests to validate patterns in the data.

    Args:
        data_dict: dict of DataFrames from extract_data()

    Returns:
        dict: mapping of test names to results
    """
    kpis = compute_kpis(data_dict)
    df = kpis["clean_df"]
    order_category_values = kpis["order_category_values"]

    results = {}

    # Test 1: t-test between top 2 real cities by customer revenue
    customer_revenue = (
        df.groupby(["customer_id", "city"], as_index=False)["line_revenue"]
        .sum()
    )

    customer_revenue_no_unknown = customer_revenue[
        customer_revenue["city"] != "Unknown"
    ].copy()

    top_cities = (
        customer_revenue_no_unknown.groupby("city")["line_revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(2)
        .index
        .tolist()
    )

    city1 = customer_revenue_no_unknown[
        customer_revenue_no_unknown["city"] == top_cities[0]
    ]["line_revenue"]

    city2 = customer_revenue_no_unknown[
        customer_revenue_no_unknown["city"] == top_cities[1]
    ]["line_revenue"]

    t_stat, p_value = stats.ttest_ind(city1, city2, equal_var=False)

    pooled_sd = np.sqrt((city1.std(ddof=1) ** 2 + city2.std(ddof=1) ** 2) / 2)
    cohens_d = (city1.mean() - city2.mean()) / pooled_sd if pooled_sd != 0 else 0.0

    results["city_revenue_ttest"] = {
        "groups": top_cities,
        "test": "Independent samples t-test",
        "statistic": float(t_stat),
        "p_value": float(p_value),
        "effect_size_cohens_d": float(cohens_d),
        "interpretation": (
            "Reject H0: customer revenue differs significantly between the top two cities."
            if p_value < 0.05
            else "Fail to reject H0: no statistically significant revenue difference between the top two cities."
        ),
    }

    # Test 2: chi-square association between city and category
    contingency = pd.crosstab(df["city"], df["category"])
    chi2, chi_p, dof, expected = stats.chi2_contingency(contingency)

    n = contingency.to_numpy().sum()
    min_dim = min(contingency.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0.0

    results["city_category_chi2"] = {
        "test": "Chi-square test of independence",
        "statistic": float(chi2),
        "p_value": float(chi_p),
        "degrees_of_freedom": int(dof),
        "effect_size_cramers_v": float(cramers_v),
        "interpretation": (
            "Reject H0: city and product category are associated."
            if chi_p < 0.05
            else "Fail to reject H0: no statistically significant association between city and product category."
        ),
    }

    # Test 3: ANOVA for category order value differences
    groups = [
        group["category_order_value"].values
        for _, group in order_category_values.groupby("category")
        if len(group) > 1
    ]

    if len(groups) >= 2:
        f_stat, f_p = stats.f_oneway(*groups)

        all_values = np.concatenate(groups)
        grand_mean = np.mean(all_values)
        ss_between = sum(len(group) * (np.mean(group) - grand_mean) ** 2 for group in groups)
        ss_total = sum(((group - grand_mean) ** 2).sum() for group in groups)
        eta_squared = ss_between / ss_total if ss_total != 0 else 0.0

        results["category_aov_anova"] = {
            "test": "One-way ANOVA",
            "statistic": float(f_stat),
            "p_value": float(f_p),
            "effect_size_eta_squared": float(eta_squared),
            "interpretation": (
                "Reject H0: average order value differs across categories."
                if f_p < 0.05
                else "Fail to reject H0: no statistically significant difference in average order value across categories."
            ),
        }

    return results


def create_visualizations(kpi_results, stat_results):
    """Create publication-quality charts for all 5 KPIs.

    Args:
        kpi_results: dict from compute_kpis()
        stat_results: dict from run_statistical_tests()

    Returns:
        None
    """
    os.makedirs("output", exist_ok=True)
    sns.set_theme(style="whitegrid")
    sns.set_palette("colorblind")

    monthly_revenue = kpi_results["monthly_revenue"]
    monthly_order_volume = kpi_results["monthly_order_volume"]
    revenue_by_city = kpi_results["revenue_by_city"]
    avg_order_value_by_category = kpi_results["avg_order_value_by_category"]
    cohort = kpi_results["revenue_by_registration_cohort"]
    order_category_values = kpi_results["order_category_values"]

    # 1) Monthly revenue
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=monthly_revenue, x="order_month", y="line_revenue", marker="o")
    plt.title("Monthly Revenue Shows the Overall Sales Trend")
    plt.xlabel("Order Month")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/monthly_revenue.png")
    plt.close()

    # 2) Monthly order volume
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=monthly_order_volume, x="order_month", y="order_count", marker="o")
    plt.title("Monthly Order Volume Tracks Demand Over Time")
    plt.xlabel("Order Month")
    plt.ylabel("Number of Orders")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/monthly_order_volume.png")
    plt.close()

    # 3) Revenue by city
    plt.figure(figsize=(10, 6))
    sns.barplot(data=revenue_by_city, x="city", y="line_revenue")
    plt.title("Revenue Is Concentrated in the Highest-Performing Cities")
    plt.xlabel("City")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/revenue_by_city.png")
    plt.close()

    # 4) Average order value by category
    plt.figure(figsize=(10, 6))
    sns.barplot(data=avg_order_value_by_category, x="category", y="category_order_value")
    plt.title("Average Order Value Differs Across Product Categories")
    plt.xlabel("Category")
    plt.ylabel("Average Order Value")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/avg_order_value_by_category.png")
    plt.close()

    # 5) Revenue by registration cohort
    plt.figure(figsize=(10, 5))
    sns.barplot(data=cohort, x="registration_month", y="line_revenue")
    plt.title("Registration Cohorts Contribute Revenue Unevenly")
    plt.xlabel("Registration Month")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/revenue_by_registration_cohort.png")
    plt.close()

    # Seaborn statistical plot
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=order_category_values, x="category", y="category_order_value")
    plt.title("Order Value Distribution Varies by Product Category")
    plt.xlabel("Category")
    plt.ylabel("Order Value")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("output/order_value_distribution_by_category.png")
    plt.close()

    # Multi-panel dashboard
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    sns.lineplot(
        data=monthly_revenue,
        x="order_month",
        y="line_revenue",
        marker="o",
        ax=axes[0, 0]
    )
    axes[0, 0].set_title("Monthly Revenue")
    axes[0, 0].tick_params(axis="x", rotation=45)

    sns.lineplot(
        data=monthly_order_volume,
        x="order_month",
        y="order_count",
        marker="o",
        ax=axes[0, 1]
    )
    axes[0, 1].set_title("Monthly Order Volume")
    axes[0, 1].tick_params(axis="x", rotation=45)

    sns.barplot(
        data=revenue_by_city,
        x="city",
        y="line_revenue",
        ax=axes[1, 0]
    )
    axes[1, 0].set_title("Revenue by City")
    axes[1, 0].tick_params(axis="x", rotation=45)

    sns.barplot(
        data=avg_order_value_by_category,
        x="category",
        y="category_order_value",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Average Order Value by Category")
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig("output/kpi_dashboard_overview.png")
    plt.close()


def main():
    """Orchestrate the full analysis pipeline."""
    os.makedirs("output", exist_ok=True)

    engine = connect_db()
    data = extract_data(engine)
    kpi_results = compute_kpis(data)
    stat_results = run_statistical_tests(data)
    create_visualizations(kpi_results, stat_results)

    print("\n=== KPI BASELINE SUMMARY ===")
    for key, value in kpi_results["baseline_summary"].items():
        print(f"{key}: {value}")

    print("\n=== STATISTICAL TEST RESULTS ===")
    for test_name, result in stat_results.items():
        print(f"\n{test_name}")
        for key, value in result.items():
            print(f"  {key}: {value}")

    print("\nCharts saved in output/")


if __name__ == "__main__":
    main()