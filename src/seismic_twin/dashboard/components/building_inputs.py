"""Building parameter input components."""

import dash_bootstrap_components as dbc
from dash import html


def create_per_floor_inputs(
    n_floors: int,
    input_type: str,
    default_value: float,
    units: str,
    id_prefix: str,
) -> html.Div:
    """
    Create input fields for per-floor/per-story values.

    Parameters
    ----------
    n_floors : int
        Number of floors/stories.
    input_type : str
        Type of input ('mass' or 'stiffness').
    default_value : float
        Default value for each input.
    units : str
        Units to display.
    id_prefix : str
        Prefix for input IDs.

    Returns
    -------
    html.Div
        Container with per-floor input fields.
    """
    inputs = []
    for i in range(n_floors):
        label = f"Floor {i + 1}" if input_type == "mass" else f"Story {i + 1}"
        inputs.append(
            dbc.InputGroup(
                [
                    dbc.InputGroupText(label, style={"width": "80px"}),
                    dbc.Input(
                        id={"type": id_prefix, "index": i},
                        type="number",
                        value=default_value,
                    ),
                    dbc.InputGroupText(units),
                ],
                className="mb-2",
                size="sm",
            )
        )

    return html.Div(inputs)


def create_parameter_summary(
    n_stories: int,
    masses: list[float],
    stiffnesses: list[float],
    damping_ratio: float,
    story_heights: list[float],
) -> dbc.Card:
    """
    Create a summary card of building parameters.

    Parameters
    ----------
    n_stories : int
        Number of stories.
    masses : list
        Floor masses in kg.
    stiffnesses : list
        Inter-story stiffnesses in N/m.
    damping_ratio : float
        Modal damping ratio.
    story_heights : list
        Story heights in meters.

    Returns
    -------
    dbc.Card
        Summary card component.
    """
    total_mass = sum(masses)
    avg_stiffness = sum(stiffnesses) / len(stiffnesses) if stiffnesses else 0
    total_height = sum(story_heights)

    return dbc.Card(
        [
            dbc.CardHeader("Building Summary"),
            dbc.CardBody(
                [
                    html.P(
                        [
                            html.Strong("Stories: "),
                            f"{n_stories}",
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Total Mass: "),
                            f"{total_mass / 1000:.1f} tonnes",
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Avg. Stiffness: "),
                            f"{avg_stiffness / 1e6:.1f} MN/m",
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Total Height: "),
                            f"{total_height:.1f} m",
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Damping: "),
                            f"{damping_ratio * 100:.1f}%",
                        ]
                    ),
                ]
            ),
        ],
        className="mb-3",
    )
