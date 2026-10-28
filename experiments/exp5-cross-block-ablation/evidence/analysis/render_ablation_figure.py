#!/usr/bin/env python3
"""Render native-size one-row Experiment 5 ablation panels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


PANEL_WIDTH_IN = 1.04
PANEL_HEIGHT_IN = 1.72
COMPOSITE_WIDTH_IN = 3.25
COMPOSITE_HEIGHT_IN = 1.85
LEGEND_WIDTH_IN = 3.25
LEGEND_HEIGHT_IN = 0.24
COMPOSITE_STEM = "exp5-ablation-three-panel"
DOMAIN_ORDER = ("memory", "u256", "stack")
DENSITY_ORDER = ("low", "medium", "high")
PANEL_STEMS = {
    "memory": "exp5-ablation-memory-panel",
    "u256": "exp5-ablation-bounded-word-panel",
    "stack": "exp5-ablation-stack-panel",
}
CONTRASTS = (
    "Cross-block target disabled",
    "Target domain disabled",
    "ReCAST core disabled",
)
FULL = "Full ReCAST"
CONFIGURATIONS = (FULL, *CONTRASTS)
DISPLAY_LABELS = {
    FULL: "Full ReCAST",
    "Cross-block target disabled": "Cross-block target disabled",
    "Target domain disabled": "Target domain disabled",
    "ReCAST core disabled": "DTVM baseline",
}
COLORS = {
    FULL: "#0072B2",
    "Cross-block target disabled": "#E69F00",
    "Target domain disabled": "#CC79A7",
    "ReCAST core disabled": "#666666",
}
HATCHES = {
    FULL: "",
    "Cross-block target disabled": "///",
    "Target domain disabled": "xxx",
    "ReCAST core disabled": "...",
}
MARKERS = {
    "Cross-block target disabled": "o",
    "Target domain disabled": "D",
    "ReCAST core disabled": "s",
}
LINESTYLES = {
    "Cross-block target disabled": "-",
    "Target domain disabled": "--",
    "ReCAST core disabled": ":",
}
RECAST_BLUE = "#0072B2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"],
            "font.size": 5.8,
            "axes.labelsize": 5.6,
            "xtick.labelsize": 4.7,
            "ytick.labelsize": 4.7,
            "axes.linewidth": 0.55,
            "xtick.major.width": 0.5,
            "ytick.major.width": 0.5,
            "xtick.major.size": 2.1,
            "ytick.major.size": 2.1,
            "hatch.linewidth": 0.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.transparent": False,
        }
    )


def plot_panel(
    domain_summary: dict[str, Any],
    ratio_axis: plt.Axes,
    time_axis: plt.Axes,
    show_y_labels: bool,
) -> None:
    for axis in (ratio_axis, time_axis):
        axis.set_axisbelow(True)
        axis.grid(axis="y", color="#D5DCE0", linewidth=0.42, zorder=0)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    positions = np.arange(len(DENSITY_ORDER), dtype=float)
    ratio_axis.axhline(
        1.0,
        color=RECAST_BLUE,
        linestyle="--",
        linewidth=0.8,
        zorder=5,
    )
    for configuration in CONTRASTS:
        results = [
            domain_summary["densities"][density]["ratios"][configuration]
            for density in DENSITY_ORDER
        ]
        estimates = np.array([float(result["estimate"]) for result in results])
        lower = np.array([float(result["ci_low"]) for result in results])
        upper = np.array([float(result["ci_high"]) for result in results])
        ratio_axis.errorbar(
            positions,
            estimates,
            yerr=np.vstack((estimates - lower, upper - estimates)),
            color=COLORS[configuration],
            linestyle=LINESTYLES[configuration],
            linewidth=0.8,
            marker=MARKERS[configuration],
            markersize=2.5,
            markerfacecolor=COLORS[configuration],
            markeredgecolor=COLORS[configuration],
            markeredgewidth=0.3,
            ecolor=COLORS[configuration],
            elinewidth=0.55,
            capsize=1.0,
            capthick=0.5,
            zorder=6,
        )
    ratio_axis.set_xlim(-0.38, 2.38)
    ratio_axis.set_ylim(0.99, 1.36)
    ratio_axis.set_yticks([1.0, 1.1, 1.2, 1.3])
    ratio_axis.set_xticks(positions)
    ratio_axis.tick_params(axis="x", labelbottom=False)
    ratio_axis.tick_params(axis="y", pad=1.0)
    if show_y_labels:
        ratio_axis.set_ylabel("Disabled / Full", labelpad=1.4)

    bar_width = 0.18
    offsets = (np.arange(len(CONFIGURATIONS)) - 1.5) * bar_width
    absolute_upper_us = 0.0
    for configuration_index, configuration in enumerate(CONFIGURATIONS):
        results = [
            domain_summary["densities"][density]["absolute_time"][configuration]
            for density in DENSITY_ORDER
        ]
        estimates = np.array(
            [float(result["estimate_ns"]) / 1000.0 for result in results]
        )
        lower = np.array(
            [float(result["ci_low_ns"]) / 1000.0 for result in results]
        )
        upper = np.array(
            [float(result["ci_high_ns"]) / 1000.0 for result in results]
        )
        absolute_upper_us = max(absolute_upper_us, float(upper.max()))
        time_axis.bar(
            positions + offsets[configuration_index],
            estimates,
            width=bar_width,
            color=COLORS[configuration],
            edgecolor="white",
            linewidth=0.28,
            hatch=HATCHES[configuration],
            yerr=np.vstack((estimates - lower, upper - estimates)),
            error_kw={"ecolor": "#222222", "elinewidth": 0.5, "capsize": 1.0},
            zorder=3,
        )
    time_axis.set_xlim(-0.48, 2.48)
    time_axis.set_ylim(0.0, absolute_upper_us * 1.14)
    time_axis.set_xticks(positions, [density.title() for density in DENSITY_ORDER])
    time_axis.tick_params(axis="x", pad=1.2)
    time_axis.tick_params(axis="y", pad=1.0)
    if show_y_labels:
        time_axis.set_ylabel(r"Warm time ($\mu$s)", labelpad=1.4)
    ratio_axis.text(
        0.5,
        1.06,
        f"n={domain_summary['case_count']}",
        transform=ratio_axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=5.2,
        fontweight="bold",
        clip_on=False,
    )


def render_panel(
    domain: str, domain_summary: dict[str, Any], show_y_labels: bool
) -> plt.Figure:
    figure = plt.figure(figsize=(PANEL_WIDTH_IN, PANEL_HEIGHT_IN))
    ratio_axis = figure.add_axes([0.22, 0.64, 0.56, 0.29])
    time_axis = figure.add_axes([0.22, 0.17, 0.56, 0.37])
    plot_panel(domain_summary, ratio_axis, time_axis, show_y_labels)
    return figure


def legend_handles() -> list[Patch]:
    return [
        Patch(
            facecolor=COLORS[configuration],
            edgecolor="white",
            linewidth=0.3,
            hatch=HATCHES[configuration],
            label=DISPLAY_LABELS[configuration],
        )
        for configuration in CONFIGURATIONS
    ]


def render_shared_legend() -> plt.Figure:
    figure = plt.figure(figsize=(LEGEND_WIDTH_IN, LEGEND_HEIGHT_IN))
    handles = legend_handles()
    figure.legend(
        handles=handles,
        labels=[DISPLAY_LABELS[configuration] for configuration in CONFIGURATIONS],
        loc="center",
        ncol=4,
        frameon=False,
        fontsize=4.7,
        handlelength=1.25,
        columnspacing=0.5,
        handletextpad=0.35,
    )
    return figure


def render_composite(summary: dict[str, Any], output_dir: Path) -> plt.Figure:
    configure_style()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(COMPOSITE_WIDTH_IN, COMPOSITE_HEIGHT_IN))
    grid = figure.add_gridspec(
        2,
        3,
        height_ratios=(0.31, 0.69),
        left=0.145,
        right=0.995,
        top=0.79,
        bottom=0.18,
        hspace=0.10,
        wspace=0.20,
    )
    for column, domain in enumerate(DOMAIN_ORDER):
        ratio_axis = figure.add_subplot(grid[0, column])
        time_axis = figure.add_subplot(grid[1, column], sharex=ratio_axis)
        ratio_axis.set_gid(f"ratio-{domain}")
        time_axis.set_gid(f"time-{domain}")
        plot_panel(
            summary["domains"][domain],
            ratio_axis,
            time_axis,
            column == 0,
        )
    handles = legend_handles()
    figure.legend(
        handles=handles,
        labels=[DISPLAY_LABELS[configuration] for configuration in CONFIGURATIONS],
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=4,
        frameon=False,
        fontsize=4.7,
        handlelength=1.25,
        columnspacing=0.5,
        handletextpad=0.35,
    )
    return figure


def render_panels(summary: dict[str, Any], output_dir: Path) -> list[plt.Figure]:
    configure_style()
    output_dir.mkdir(parents=True, exist_ok=True)
    figures = []
    for index, domain in enumerate(DOMAIN_ORDER):
        figure = render_panel(domain, summary["domains"][domain], index == 0)
        stem = output_dir / PANEL_STEMS[domain]
        figure.savefig(stem.with_suffix(".pdf"), dpi=600)
        figure.savefig(stem.with_suffix(".svg"), dpi=600)
        figure.savefig(stem.with_suffix(".png"), dpi=600)
        figures.append(figure)
    return figures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    figures = render_panels(summary, args.output_dir)
    legend = render_shared_legend()
    composite = render_composite(summary, args.output_dir)
    legend_stem = args.output_dir / "exp5-ablation-shared-legend"
    for extension in ("pdf", "svg", "png"):
        legend.savefig(legend_stem.with_suffix(f".{extension}"), dpi=600)
    composite_stem = args.output_dir / COMPOSITE_STEM
    for extension in ("pdf", "svg", "png"):
        composite.savefig(composite_stem.with_suffix(f".{extension}"), dpi=600)
    for figure in figures:
        plt.close(figure)
    plt.close(legend)
    panel_centers = [
        (axis.get_position().x0 + axis.get_position().x1) / 2.0
        for axis in composite.axes[0::2]
    ]
    plotting_width_in = (
        composite.axes[0].get_position().width * COMPOSITE_WIDTH_IN
    )
    plt.close(composite)
    outputs = [
        args.output_dir / f"{PANEL_STEMS[domain]}.{extension}"
        for domain in DOMAIN_ORDER
        for extension in ("pdf", "svg", "png")
    ] + [
        legend_stem.with_suffix(f".{extension}")
        for extension in ("pdf", "svg", "png")
    ] + [
        composite_stem.with_suffix(f".{extension}")
        for extension in ("pdf", "svg", "png")
    ]
    provenance = {
        "schema_version": 3,
        "summary_sha256": sha256(args.summary),
        "native_panel_width_in": PANEL_WIDTH_IN,
        "native_panel_height_in": PANEL_HEIGHT_IN,
        "shared_legend_width_in": LEGEND_WIDTH_IN,
        "shared_legend_height_in": LEGEND_HEIGHT_IN,
        "composite_width_in": COMPOSITE_WIDTH_IN,
        "composite_height_in": COMPOSITE_HEIGHT_IN,
        "composite_plotting_width_in": plotting_width_in,
        "composite_panel_centers": panel_centers,
        "layout": "single-column integrated one-row three-panel",
        "latex_panel_names_required": True,
        "outputs": {str(path.name): sha256(path) for path in outputs},
    }
    args.provenance.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(provenance, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
