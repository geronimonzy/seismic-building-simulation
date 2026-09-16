"""Base layout components: navbar and sidebar."""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar() -> dbc.Navbar:
    """Create the top navigation bar."""
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.A(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.I(
                                                className="bi bi-building",
                                                style={"fontSize": "1.5rem"},
                                            ),
                                            width="auto",
                                        ),
                                        dbc.Col(
                                            dbc.NavbarBrand(
                                                "Seismic Twin",
                                                className="ms-2 fw-bold",
                                            ),
                                        ),
                                    ],
                                    align="center",
                                    className="g-0",
                                ),
                                href="/",
                                style={"textDecoration": "none"},
                            ),
                        ),
                    ],
                    align="center",
                    className="g-0",
                ),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(
                                dbc.NavLink(
                                    [html.I(className="bi bi-github me-1"), "GitHub"],
                                    href="https://github.com/geronimonzy/seismic-building-simulation",
                                    external_link=True,
                                    target="_blank",
                                )
                            ),
                        ],
                        className="ms-auto",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="primary",
        dark=True,
        className="mb-0",
    )


def create_sidebar() -> html.Div:
    """Create the sidebar navigation."""
    nav_items = [
        {"href": "/", "icon": "bi-building", "label": "Building", "id": "nav-building"},
        {
            "href": "/ground-motion",
            "icon": "bi-activity",
            "label": "Ground Motion",
            "id": "nav-ground-motion",
        },
        {
            "href": "/simulation",
            "icon": "bi-play-circle",
            "label": "Simulation",
            "id": "nav-simulation",
        },
        {
            "href": "/results",
            "icon": "bi-graph-up",
            "label": "Results",
            "id": "nav-results",
        },
        {
            "href": "/wave-prediction",
            "icon": "bi-broadcast-pin",
            "label": "Wave Prediction",
            "id": "nav-wave-prediction",
        },
    ]

    nav_links = []
    for item in nav_items:
        nav_links.append(
            dbc.NavLink(
                [
                    html.I(className=f"bi {item['icon']} me-2"),
                    item["label"],
                ],
                href=item["href"],
                id=item["id"],
                active="exact",
                className="sidebar-link",
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.H6("Navigation", className="sidebar-heading text-muted px-3 mt-3 mb-2"),
                    dbc.Nav(
                        nav_links,
                        vertical=True,
                        pills=True,
                        className="flex-column",
                    ),
                ],
                className="sidebar-sticky",
            ),
            html.Hr(className="my-3"),
            html.Div(
                [
                    html.H6("Quick Info", className="sidebar-heading text-muted px-3 mb-2"),
                    html.Div(
                        id="sidebar-info",
                        className="px-3 small text-muted",
                        children=[
                            html.P("Building: Not configured", id="sidebar-building-info"),
                            html.P("Ground Motion: None", id="sidebar-gm-info"),
                            html.P("Simulation: Not run", id="sidebar-sim-info"),
                        ],
                    ),
                ],
            ),
        ],
        className="sidebar bg-light border-end",
        style={
            "position": "fixed",
            "top": "56px",  # Below navbar
            "left": 0,
            "bottom": 0,
            "width": "220px",
            "padding": "0",
            "overflowY": "auto",
        },
    )


def create_main_content_wrapper(content: html.Div) -> html.Div:
    """Wrap main content with proper margin for sidebar."""
    return html.Div(
        content,
        style={
            "marginLeft": "220px",
            "padding": "20px",
        },
    )


def create_page_header(title: str, subtitle: str = "") -> html.Div:
    """Create a consistent page header."""
    return html.Div(
        [
            html.H3(title, className="mb-1"),
            html.P(subtitle, className="text-muted") if subtitle else None,
            html.Hr(className="my-3"),
        ],
        className="mb-4",
    )
