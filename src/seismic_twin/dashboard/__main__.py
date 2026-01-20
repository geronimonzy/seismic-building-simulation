"""
Entry point for running the dashboard as a module.

Usage:
    python -m seismic_twin.dashboard
    python -m seismic_twin.dashboard --port 8051
    python -m seismic_twin.dashboard --debug
"""

import argparse


def main():
    """Run the dashboard development server."""
    parser = argparse.ArgumentParser(
        description="Seismic Twin Interactive Dashboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with hot reloading",
    )

    args = parser.parse_args()

    from seismic_twin.dashboard import create_app

    app = create_app(debug=args.debug)

    print(f"\nStarting Seismic Twin Dashboard...")
    print(f"Open http://{args.host}:{args.port} in your browser\n")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
