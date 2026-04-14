import dash
from dash import html, dcc, callback, Input, Output

from dash_data import (
    CLEAN_DF,
    MIN_DATE,
    MAX_DATE,
    filter_clean_df,
    build_monthly_revenue_figure,
    build_monthly_order_volume_figure,
)

dash.register_page(__name__, path="/time-series")

layout = html.Div(
    [
        html.H2("Page 2: Time-Series Deep Dive"),
        html.P("This page reads the selected city from Page 1 and also applies a date range filter."),

        html.Div(id="time-series-city-label", className="info-label"),

        dcc.DatePickerRange(
            id="ts-date-range",
            min_date_allowed=MIN_DATE,
            max_date_allowed=MAX_DATE,
            start_date=MIN_DATE,
            end_date=MAX_DATE,
            display_format="YYYY-MM-DD",
            className="control"
        ),

        dcc.Graph(id="ts-revenue-graph"),
        dcc.Graph(id="ts-orders-graph"),
    ],
    className="page-shell"
)


@callback(
    Output("ts-revenue-graph", "figure"),
    Output("ts-orders-graph", "figure"),
    Output("time-series-city-label", "children"),
    Input("global-filters", "data"),
    Input("ts-date-range", "start_date"),
    Input("ts-date-range", "end_date"),
)
def update_time_series(global_filters, start_date, end_date):
    selected_city = (global_filters or {}).get("city", "All")

    filtered_df = filter_clean_df(
        CLEAN_DF,
        city=selected_city,
        start_date=start_date,
        end_date=end_date,
    )

    revenue_fig = build_monthly_revenue_figure(
        filtered_df,
        f"Monthly Revenue — City: {selected_city}"
    )
    orders_fig = build_monthly_order_volume_figure(
        filtered_df,
        f"Monthly Order Volume — City: {selected_city}"
    )

    return revenue_fig, orders_fig, f"Selected city from Page 1: {selected_city}"