import dash
from dash import html, dcc, callback, Input, Output

from dash_data import (
    CLEAN_DF,
    filter_clean_df,
    build_cohort_comparison_figure,
    build_cohort_drilldown_figure,
)

dash.register_page(__name__, path="/cohorts")

layout = html.Div(
    [
        html.H2("Page 3: Cohort Comparison"),
        html.P("Click a cohort bar to drill down into category revenue for that cohort."),

        html.Div(id="cohort-city-label", className="info-label"),
        html.Div(id="cohort-selected-label", className="info-label"),

        dcc.Graph(id="cohort-main-graph"),
        dcc.Graph(id="cohort-drilldown-graph"),
    ],
    className="page-shell"
)


@callback(
    Output("cohort-main-graph", "figure"),
    Output("cohort-city-label", "children"),
    Input("global-filters", "data"),
)
def update_cohort_main(global_filters):
    selected_city = (global_filters or {}).get("city", "All")
    filtered_df = filter_clean_df(CLEAN_DF, city=selected_city)

    fig = build_cohort_comparison_figure(
        filtered_df,
        f"Cohort Comparison — City: {selected_city}"
    )

    return fig, f"Selected city from Page 1: {selected_city}"


@callback(
    Output("cohort-drilldown-graph", "figure"),
    Output("cohort-selected-label", "children"),
    Input("cohort-main-graph", "clickData"),
    Input("global-filters", "data"),
)
def update_cohort_drilldown(click_data, global_filters):
    selected_city = (global_filters or {}).get("city", "All")
    filtered_df = filter_clean_df(CLEAN_DF, city=selected_city)


    selected_cohort = None
    if click_data and "points" in click_data and click_data["points"]:
        point = click_data["points"][0]

        if "x" in point:
            selected_cohort = point["x"]
            if selected_cohort is not None:
                selected_cohort = str(selected_cohort)

    fig = build_cohort_drilldown_figure(
        filtered_df,
        selected_cohort,
        f"Cohort Drill-Down — City: {selected_city}"
    )

    label = (
        f"Selected cohort: {selected_cohort}"
        if selected_cohort
        else "Click a cohort bar to see drill-down details."
    )

    return fig, label