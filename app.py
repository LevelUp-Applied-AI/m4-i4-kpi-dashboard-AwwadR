from dash import Dash, html, dcc
import dash

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    [
        dcc.Store(id="global-filters", storage_type="session", data={"city": "All"}),

        html.H1("Amman Digital Market Multi-Page Analytical Report", className="main-title"),

        html.Div(
            [
                dcc.Link("Page 1: KPI Overview", href="/", className="nav-link"),
                dcc.Link("Page 2: Time-Series Deep Dive", href="/time-series", className="nav-link"),
                dcc.Link("Page 3: Cohort Comparison", href="/cohorts", className="nav-link"),
            ],
            className="nav-bar"
        ),

        html.Hr(),

        dash.page_container,
    ],
    className="app-shell"
)

if __name__ == "__main__":
    app.run(debug=True)