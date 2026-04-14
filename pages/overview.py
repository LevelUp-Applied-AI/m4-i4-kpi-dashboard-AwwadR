import dash
from dash import html, dcc, callback, Input, Output

from dash_data import CLEAN_DF, CONFIG, CITIES, filter_clean_df, build_monitoring_summary_from_clean_df, make_gauge_figure

dash.register_page(__name__, path="/")

layout = html.Div(
    [
        html.H2("Page 1: KPI Overview"),
        html.P("Choose a city here. This selection will filter Pages 2 and 3."),

        dcc.Dropdown(
            id="overview-city-dropdown",
            options=[{"label": city, "value": city} for city in CITIES],
            value="All",
            clearable=False,
            className="control"
        ),

        html.Div(id="overview-city-label", className="info-label"),

        dcc.Graph(id="overview-gauge-graph"),
    ],
    className="page-shell"
)


@callback(
    Output("overview-gauge-graph", "figure"),
    Output("global-filters", "data"),
    Output("overview-city-label", "children"),
    Input("overview-city-dropdown", "value"),
)
def update_overview(selected_city):
    filtered_df = filter_clean_df(CLEAN_DF, city=selected_city)
    summary = build_monitoring_summary_from_clean_df(filtered_df, CONFIG)
    fig = make_gauge_figure(summary, f"KPI Overview — City: {selected_city}")

    return fig, {"city": selected_city}, f"Selected city: {selected_city}"