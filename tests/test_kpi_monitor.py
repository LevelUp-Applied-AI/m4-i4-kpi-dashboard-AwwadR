import json
import pandas as pd

from kpi_monitor import (
    evaluate_kpi_status,
    prepare_clean_df,
    compute_kpis,
    compute_kpis_from_clean_df,
    build_monitoring_summary,
    build_monitoring_summary_from_clean_df,
    load_config,
    create_monitor_dashboard_with_filters,
)


def make_mock_data():
    customers = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "city": ["Amman", "Zarqa", "Amman"],
        "registration_date": ["2024-01-05", "2024-02-10", "2024-03-15"],
    })

    products = pd.DataFrame({
        "product_id": [101, 102, 103],
        "category": ["Books", "Electronics", "Books"],
    })

    orders = pd.DataFrame({
        "order_id": [1001, 1002, 1003, 1004],
        "customer_id": [1, 2, 3, 1],
        "order_date": ["2024-04-01", "2024-05-01", "2024-06-01", "2024-07-01"],
        "status": ["completed", "completed", "cancelled", "completed"],
    })

    order_items = pd.DataFrame({
        "order_id": [1001, 1002, 1003, 1004],
        "product_id": [101, 102, 103, 101],
        "quantity": [2, 1, 3, 2],
        "unit_price": [20.0, 100.0, 25.0, 30.0],
    })

    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
    }


def make_mock_config():
    return {
        "monthly_revenue": {"target": 50, "warning_ratio": 0.9},
        "monthly_order_volume": {"target": 1, "warning_ratio": 0.9},
        "revenue_by_city": {"target": 60, "warning_ratio": 0.9},
        "avg_order_value_by_category": {"target": 40, "warning_ratio": 0.9},
        "revenue_by_registration_cohort": {"target": 50, "warning_ratio": 0.9},
    }


def test_evaluate_kpi_status_green():
    status = evaluate_kpi_status(actual=100, target=100, warning_ratio=0.9)
    assert status == "green"


def test_evaluate_kpi_status_yellow():
    status = evaluate_kpi_status(actual=95, target=100, warning_ratio=0.9)
    assert status == "yellow"


def test_evaluate_kpi_status_red():
    status = evaluate_kpi_status(actual=80, target=100, warning_ratio=0.9)
    assert status == "red"


def test_prepare_clean_df_filters_cancelled_orders():
    data = make_mock_data()
    clean_df = prepare_clean_df(data)

    assert "line_revenue" in clean_df.columns
    assert "order_month" in clean_df.columns
    assert "registration_month" in clean_df.columns

    # order_id 1003 is cancelled, so it should be removed
    assert 1003 not in clean_df["order_id"].values


def test_compute_kpis_returns_expected_keys():
    data = make_mock_data()
    kpis = compute_kpis(data)

    expected_keys = {
        "clean_df",
        "order_totals",
        "monthly_revenue",
        "monthly_order_volume",
        "revenue_by_city",
        "avg_order_value_by_category",
        "revenue_by_registration_cohort",
    }

    assert expected_keys.issubset(set(kpis.keys()))


def test_compute_kpis_with_mock_data_has_non_empty_outputs():
    data = make_mock_data()
    kpis = compute_kpis(data)

    assert not kpis["clean_df"].empty
    assert not kpis["monthly_revenue"].empty
    assert not kpis["monthly_order_volume"].empty
    assert not kpis["revenue_by_city"].empty


def test_build_monitoring_summary_returns_expected_structure():
    data = make_mock_data()
    config = make_mock_config()
    kpis = compute_kpis(data)

    summary = build_monitoring_summary(kpis, config)

    expected_kpis = {
        "monthly_revenue",
        "monthly_order_volume",
        "revenue_by_city",
        "avg_order_value_by_category",
        "revenue_by_registration_cohort",
    }

    assert expected_kpis == set(summary.keys())

    for kpi_name, values in summary.items():
        assert "actual" in values
        assert "target" in values
        assert "status" in values
        assert values["status"] in {"green", "yellow", "red"}


def test_build_monitoring_summary_from_clean_df_handles_empty_df():
    config = make_mock_config()

    empty_df = pd.DataFrame(columns=[
        "customer_id",
        "city",
        "registration_date",
        "product_id",
        "category",
        "order_id",
        "order_date",
        "quantity",
        "unit_price",
        "line_revenue",
        "order_month",
        "registration_month",
    ])

    summary = build_monitoring_summary_from_clean_df(empty_df, config)

    assert summary["monthly_revenue"]["actual"] == 0.0
    assert summary["monthly_order_volume"]["actual"] == 0
    assert summary["revenue_by_city"]["actual"] == 0.0
    assert summary["avg_order_value_by_category"]["actual"] == 0.0
    assert summary["revenue_by_registration_cohort"]["actual"] == 0.0


def test_load_config_reads_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_data = make_mock_config()

    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    loaded = load_config(str(config_path))

    assert loaded == config_data


def test_create_monitor_dashboard_with_filters_writes_html(tmp_path, monkeypatch):
    data = make_mock_data()
    config = make_mock_config()
    clean_df = prepare_clean_df(data)

    monkeypatch.chdir(tmp_path)

    create_monitor_dashboard_with_filters(clean_df, config)

    output_file = tmp_path / "output" / "kpi_monitor.html"
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "KPI Monitoring Dashboard" in content
    assert "City Filter Monitoring" in content
    assert "Category Filter Monitoring" in content
    assert "Date Range Filter Monitoring" in content


def test_compute_kpis_from_clean_df_matches_prepare_clean_df_flow():
    data = make_mock_data()
    clean_df = prepare_clean_df(data)

    kpis_from_clean = compute_kpis_from_clean_df(clean_df)
    kpis_direct = compute_kpis(data)

    assert len(kpis_from_clean["clean_df"]) == len(kpis_direct["clean_df"])
    assert len(kpis_from_clean["monthly_revenue"]) == len(kpis_direct["monthly_revenue"])
    assert len(kpis_from_clean["monthly_order_volume"]) == len(kpis_direct["monthly_order_volume"])