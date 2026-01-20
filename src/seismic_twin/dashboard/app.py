"""
Dash application factory for the Seismic Twin dashboard.

This module creates and configures the main Dash application with multi-page
support, Bootstrap theming, and background callback management.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, page_container

from seismic_twin.dashboard.callbacks import register_all_callbacks
from seismic_twin.dashboard.layouts import (
    create_building_layout,
    create_ground_motion_layout,
    create_navbar,
    create_results_layout,
    create_sidebar,
    create_simulation_layout,
)
from seismic_twin.dashboard.state import create_stores


def create_app(debug: bool = False) -> Dash:
    """
    Create and configure the Dash application.

    Parameters
    ----------
    debug : bool
        If True, enable debug mode with hot reloading.

    Returns
    -------
    Dash
        Configured Dash application instance.
    """
    # Create Dash app with Bootstrap theme
    app = Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            dbc.icons.BOOTSTRAP,  # Bootstrap Icons
        ],
        suppress_callback_exceptions=True,
        title="Seismic Twin Dashboard",
        update_title="Loading...",
    )

    # Define the app layout
    app.layout = html.Div(
        [
            # URL routing
            dcc.Location(id="url", refresh=False),
            # State stores
            *create_stores(),
            # Navigation bar
            create_navbar(),
            # Main content area with sidebar
            html.Div(
                [
                    # Sidebar
                    create_sidebar(),
                    # Page content
                    html.Div(
                        id="page-content",
                        style={
                            "marginLeft": "220px",
                            "padding": "20px",
                            "minHeight": "calc(100vh - 56px)",
                        },
                    ),
                ],
            ),
        ]
    )

    # Page routing map
    page_routes = {
        "/": create_building_layout,
        "/building": create_building_layout,
        "/ground-motion": create_ground_motion_layout,
        "/simulation": create_simulation_layout,
        "/results": create_results_layout,
    }

    # Register URL routing callback
    @app.callback(
        dash.Output("page-content", "children"),
        dash.Input("url", "pathname"),
    )
    def display_page(pathname: str) -> html.Div:
        """Route to the appropriate page based on URL."""
        layout_fn = page_routes.get(pathname)
        if layout_fn is not None:
            return layout_fn()
        # 404 page
        return html.Div(
            [
                html.H3("404 - Page Not Found"),
                html.P(f"The page '{pathname}' does not exist."),
                html.A("Go to home", href="/"),
            ],
            className="text-center mt-5",
        )

    # Register all callbacks
    register_all_callbacks(app)

    return app


def create_server():
    """
    Create the Flask server for production deployment.

    This function is used by gunicorn:
        gunicorn "seismic_twin.dashboard:create_server()"

    Returns
    -------
    Flask
        Flask server instance.
    """
    app = create_app(debug=False)
    return app.server


# Create app instance for import
app = create_app()
server = app.server
