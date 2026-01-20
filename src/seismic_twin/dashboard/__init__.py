"""
Seismic Twin Interactive Dashboard

A Plotly Dash web application for interactive seismic building simulation.

Usage
-----
Development mode:
    python -m seismic_twin.dashboard

Production mode:
    gunicorn "seismic_twin.dashboard:create_server()" -b 0.0.0.0:8050

Docker:
    docker compose -f docker-compose.dashboard.yml up
"""

from seismic_twin.dashboard.app import app, create_app, create_server, server

__all__ = [
    "app",
    "server",
    "create_app",
    "create_server",
]
