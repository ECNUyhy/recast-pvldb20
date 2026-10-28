"""Shared visual primitives for Experiment 2 paper figures."""

from __future__ import annotations

from typing import Any


RECAST_BLUE = "#0072B2"
REFERENCE_LINE_ZORDER = 5
GRID_ZORDER = 0


def draw_recast_reference_line(axis: Any, *, linewidth: float = 0.9) -> Any:
    """Draw the ReCAST=1 reference above a coincident horizontal gridline."""
    return axis.axhline(
        1.0,
        color=RECAST_BLUE,
        linestyle="--",
        linewidth=linewidth,
        zorder=REFERENCE_LINE_ZORDER,
    )


def draw_horizontal_grid(axis: Any, *, linewidth: float = 0.45) -> None:
    """Draw the subdued paper grid behind data and reference lines."""
    axis.grid(axis="y", color="#D5DCE0", linewidth=linewidth, zorder=GRID_ZORDER)
