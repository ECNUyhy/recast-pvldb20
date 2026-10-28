#!/usr/bin/env python3
"""Render Figures 7 and 8 from the released Experiment 2 aggregate CSVs.

The module plots the released point estimates and confidence intervals as is.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import Bbox
import numpy as np
import pandas as pd


PERFORMANCE_DIR = Path(__file__).resolve().parents[1]
if str(PERFORMANCE_DIR) not in sys.path:
    sys.path.insert(0, str(PERFORMANCE_DIR))

from figure_style import (  # noqa: E402
    RECAST_BLUE,
    draw_horizontal_grid,
    draw_recast_reference_line,
)


FIGURE_WIDTH_IN = 7.05
# Native figure sizes at the two-column width.
STEADY_HEIGHT_IN = 2.35
ONLINE_HEIGHT_IN = 2.10
ONLINE_HALF_COLUMN_WIDTH_IN = 1.56
ONLINE_HALF_COLUMN_HEIGHT_IN = 1.37
ONLINE_LEGEND_WIDTH_IN = 3.25
ONLINE_LEGEND_HEIGHT_IN = 0.24
REVM_C_GREEN = "#009E73"
ENGINES = ["ReCAST", "evmone 0.22.0", "REVM 42.0.1", "Geth 1.17.5"]
DISPLAY = {
    "ReCAST": "ReCAST",
    "evmone 0.22.0": "evmone",
    "REVM 42.0.1": "REVM",
    "Geth 1.17.5": "Geth",
}
COLORS = {
    "ReCAST": RECAST_BLUE,
    "evmone 0.22.0": "#CC79A7",
    "REVM 42.0.1": "#E69F00",
    "Geth 1.17.5": "#666666",
}
HATCHES = {
    "ReCAST": "",
    "evmone 0.22.0": "///",
    "REVM 42.0.1": "xxx",
    "Geth 1.17.5": "...",
}
MARKERS = {
    "evmone 0.22.0": "D",
    "REVM 42.0.1": "^",
    "Geth 1.17.5": "s",
}
PANEL_ORDER = ["general", "memory", "bounded_word", "stack"]
PANEL_CAPTIONS = {
    "general": "(a) General",
    "memory": "(b) Memory",
    "bounded_word": "(c) Bounded word",
    "stack": "(d) Stack/control flow",
}
CASE_LABELS = {
    "general": {
        "erc20-approval-transfer": "A+T",
        "erc20-mint": "Mint",
        "erc20-transfer": "Tx",
        "snailtracer": "Snail",
        "ten-thousand-hashes": "10kHash",
        "structarray_alloc-nfts_rank": "Struct",
        "weierstrudel-1": "W1",
        "weierstrudel-15": "W15",
    },
    "memory": {
        "memory_grow_mload-nogrow": "0",
        "memory_grow_mload-by1": "+1",
        "memory_grow_mload-by16": "+16",
        "memory_grow_mload-by32": "+32",
        "memory_grow_mstore-nogrow": "0",
        "memory_grow_mstore-by1": "+1",
        "memory_grow_mstore-by16": "+16",
        "memory_grow_mstore-by32": "+32",
    },
    "bounded_word": {
        "blake2b_huff-empty": "B2H-E",
        "blake2b_huff-8415nulls": "B2H-N",
        "blake2b_shifts-8415nulls": "B2S-N",
        "sha1_divs-empty": "S1D-E",
        "sha1_divs-5311": "S1D-5k",
        "sha1_shifts-empty": "S1S-E",
        "sha1_shifts-5311": "S1S-5k",
    },
    "stack": {
        "swap_math-spent": "swap\nspent",
        "swap_math-received": "swap\nrecv",
        "swap_math-insufficient_liquidity": "swap\nfail",
        "jump_around-empty": "jump\naround",
        "loop_with_many_jumpdests-empty": "many\nJDEST",
    },
}


STEADY_SOURCES = {
    "general": Path(
        "system-comparison/public-contract-cohort/"
        "analysis/workload-summary.csv"
    ),
    "memory": Path(
        "memory-steady-state/analysis/memory-system-summary.csv"
    ),
    "bounded_word": Path(
        "bounded-word-steady-state/analysis/"
        "bounded-word-interpreter-steady-state-single-column-by-case.csv"
    ),
    "stack": Path(
        "stack-steady-state/analysis/"
        "stack-control-flow-interpreter-steady-state-single-column-by-case.csv"
    ),
}
ONLINE_SOURCES = {
    "general": Path(
        "online-total-latency/public-contract-online/"
        "analysis/online-total-latency-by-n.csv"
    ),
    "memory": Path(
        "memory-online/analysis/"
        "memory-online-total-latency-single-column-by-n.csv"
    ),
    "bounded_word": Path(
        "bounded-word-online/analysis/"
        "bounded-word-online-total-latency-single-column-by-n.csv"
    ),
    "stack": Path(
        "stack-online/analysis/"
        "stack-control-flow-online-total-latency-single-column-by-n.csv"
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_engine(value: str) -> str:
    return {
        "evmone": "evmone 0.22.0",
        "REVM": "REVM 42.0.1",
        "Geth": "Geth 1.17.5",
    }.get(value, value)


def _normalize_steady(key: str, frame: pd.DataFrame) -> pd.DataFrame:
    if key == "general":
        columns = {
            "workload": "case",
            "warm_time_us": "value",
            "warm_ci95_low_us": "low",
            "warm_ci95_high_us": "high",
            "time_over_recast": "ratio",
            "ratio_ci95_low": "ratio_low",
            "ratio_ci95_high": "ratio_high",
        }
    elif key == "memory":
        columns = {
            "warm_us": "value",
            "ci95_low_us": "low",
            "ci95_high_us": "high",
            "time_over_ReCAST": "ratio",
            "ratio_ci95_low": "ratio_low",
            "ratio_ci95_high": "ratio_high",
        }
    else:
        columns = {
            "median_us": "value",
            "ci95_low_us": "low",
            "ci95_high_us": "high",
            "ratio_to_recast": "ratio",
            "ratio_ci95_low": "ratio_low",
            "ratio_ci95_high": "ratio_high",
        }
    normalized = frame.rename(columns=columns).copy()
    normalized["engine"] = normalized["engine"].map(_normalize_engine)
    normalized = normalized[normalized["engine"].isin(ENGINES)]
    required = [
        "case",
        "engine",
        "value",
        "low",
        "high",
        "ratio",
        "ratio_low",
        "ratio_high",
    ]
    return normalized[required].reset_index(drop=True)


def load_steady_cohorts(root: Path) -> dict[str, pd.DataFrame]:
    return {
        key: _normalize_steady(key, pd.read_csv(root / source))
        for key, source in STEADY_SOURCES.items()
    }


def _normalize_online(key: str, frame: pd.DataFrame) -> pd.DataFrame:
    if key == "general":
        columns = {
            "ReCAST_total_ms": "recast",
            "ReCAST_ci95_low_ms": "recast_low",
            "ReCAST_ci95_high_ms": "recast_high",
            "revmc_total_ms": "revmc",
            "revmc_ci95_low_ms": "revmc_low",
            "revmc_ci95_high_ms": "revmc_high",
            "revmc_over_ReCAST": "ratio",
            "ratio_ci95_low": "ratio_low",
            "ratio_ci95_high": "ratio_high",
        }
    else:
        columns = {
            "recast_ms": "recast",
            "recast_ci_low_ms": "recast_low",
            "recast_ci_high_ms": "recast_high",
            "revmc_ms": "revmc",
            "revmc_ci_low_ms": "revmc_low",
            "revmc_ci_high_ms": "revmc_high",
            "revmc_over_recast": "ratio",
            "ratio_ci_low": "ratio_low",
            "ratio_ci_high": "ratio_high",
        }
    required = [
        "N",
        "recast",
        "recast_low",
        "recast_high",
        "revmc",
        "revmc_low",
        "revmc_high",
        "ratio",
        "ratio_low",
        "ratio_high",
    ]
    return frame.rename(columns=columns)[required].sort_values("N").reset_index(drop=True)


def load_online_cohorts(root: Path) -> dict[str, pd.DataFrame]:
    return {
        key: _normalize_online(key, pd.read_csv(root / source))
        for key, source in ONLINE_SOURCES.items()
    }


def _set_paper_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
            "font.size": 6.0,
            "axes.labelsize": 6.2,
            "xtick.labelsize": 5.0,
            "ytick.labelsize": 5.2,
            "legend.fontsize": 6.0,
            "axes.linewidth": 0.65,
            "lines.linewidth": 0.85,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "hatch.linewidth": 0.35,
        }
    )


def _new_composite(
    *,
    figure_height_in: float,
    interpanel_hspace: float,
    height_ratios: tuple[float, float],
    top: float,
    bottom: float,
) -> tuple[plt.Figure, list[tuple[plt.Axes, plt.Axes]]]:
    _set_paper_style()
    figure = plt.figure(figsize=(FIGURE_WIDTH_IN, figure_height_in))
    grid = figure.add_gridspec(
        2,
        4,
        height_ratios=height_ratios,
        left=0.058,
        right=0.995,
        top=top,
        bottom=bottom,
        hspace=interpanel_hspace,
        wspace=0.35,
    )
    axes: list[tuple[plt.Axes, plt.Axes]] = []
    for column, key in enumerate(PANEL_ORDER):
        ratio_axis = figure.add_subplot(grid[0, column])
        time_axis = figure.add_subplot(grid[1, column], sharex=ratio_axis)
        ratio_axis.set_gid(f"ratio-{key}")
        time_axis.set_gid(f"time-{key}")
        axes.append((ratio_axis, time_axis))
    return figure, axes


def _configure_axis(axis: plt.Axes) -> None:
    draw_horizontal_grid(axis)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(width=0.6, length=2.4, pad=1.5)


def _powers_of_two_ticks(maximum: float) -> list[float]:
    upper_power = max(1, int(np.ceil(np.log2(maximum))))
    step = 2 if upper_power >= 7 else 1
    powers = list(range(0, upper_power + 1, step))
    if powers[-1] != upper_power:
        powers.append(upper_power)
    return [float(2**power) for power in powers]


def _plot_steady_panel(
    key: str,
    frame: pd.DataFrame,
    ratio_axis: plt.Axes,
    time_axis: plt.Axes,
    column: int,
) -> None:
    cases = list(CASE_LABELS[key])
    x = np.arange(len(cases), dtype=float)
    width = 0.19
    offsets = np.linspace(-1.5 * width, 1.5 * width, len(ENGINES))
    maximum_time_high = 0.0

    _configure_axis(ratio_axis)
    _configure_axis(time_axis)
    draw_recast_reference_line(ratio_axis, linewidth=1.05)

    maximum_ratio = 1.0
    for engine in ENGINES[1:]:
        ordered = frame[frame["engine"] == engine].set_index("case").loc[cases]
        values = ordered["ratio"].to_numpy()
        lower = values - ordered["ratio_low"].to_numpy()
        upper = ordered["ratio_high"].to_numpy() - values
        maximum_ratio = max(maximum_ratio, float(np.max(ordered["ratio_high"])))
        ratio_axis.errorbar(
            x,
            values,
            yerr=np.vstack([lower, upper]),
            color=COLORS[engine],
            marker=MARKERS[engine],
            markersize=2.6,
            markeredgecolor="white",
            markeredgewidth=0.25,
            capsize=1.1,
            elinewidth=0.55,
            zorder=4,
        )

    ratio_axis.set_yscale("log", base=2)
    ratio_ticks = _powers_of_two_ticks(maximum_ratio)
    ratio_axis.set_yticks(ratio_ticks)
    ratio_axis.set_yticklabels([f"{int(value)}x" for value in ratio_ticks])
    ratio_axis.set_ylim(0.88, max(ratio_ticks[-1] * 1.28, 2.2))
    ratio_axis.tick_params(axis="x", labelbottom=False, bottom=False)
    if column == 0:
        ratio_axis.set_ylabel("Time / ReCAST", labelpad=2.0)

    for offset, engine in zip(offsets, ENGINES):
        ordered = frame[frame["engine"] == engine].set_index("case").loc[cases]
        values = ordered["value"].to_numpy()
        lower = values - ordered["low"].to_numpy()
        upper = ordered["high"].to_numpy() - values
        maximum_time_high = max(maximum_time_high, float(np.max(ordered["high"])))
        time_axis.bar(
            x + offset,
            values,
            width=width,
            color=COLORS[engine],
            edgecolor="white",
            linewidth=0.28,
            hatch=HATCHES[engine],
            yerr=np.vstack([lower, upper]),
            error_kw={"elinewidth": 0.5, "capsize": 1.0, "capthick": 0.5},
            zorder=3,
        )
    time_axis.set_yscale("log")
    time_axis.set_xticks(x)
    rotation = 52 if key in {"general", "bounded_word"} else 0
    time_axis.set_xticklabels(
        [CASE_LABELS[key][case] for case in cases],
        rotation=rotation,
        ha="right" if rotation else "center",
        rotation_mode="anchor",
    )
    time_axis.set_xlim(-0.62, len(cases) - 0.38)
    if column == 0:
        time_axis.set_ylabel("Warm time (µs)", labelpad=2.0)

    if key == "memory":
        ratio_axis.axvline(3.5, color="#C8CDD0", linewidth=0.55, zorder=1)
        time_axis.axvline(3.5, color="#C8CDD0", linewidth=0.55, zorder=1)
        lower_limit, _ = time_axis.get_ylim()
        time_axis.set_ylim(lower_limit, maximum_time_high * 2.0)
        time_axis.text(1.5, 0.965, "MLOAD", transform=time_axis.get_xaxis_transform(), ha="center", va="top", fontsize=5.0, fontweight="bold")
        time_axis.text(5.5, 0.965, "MSTORE", transform=time_axis.get_xaxis_transform(), ha="center", va="top", fontsize=5.0, fontweight="bold")


def render_steady_composite(root: Path) -> plt.Figure:
    cohorts = load_steady_cohorts(root)
    figure, axes = _new_composite(
        figure_height_in=STEADY_HEIGHT_IN,
        interpanel_hspace=0.08,
        height_ratios=(0.32, 0.68),
        top=0.83,
        bottom=0.13,
    )
    for column, key in enumerate(PANEL_ORDER):
        _plot_steady_panel(key, cohorts[key], *axes[column], column)

    handles = [
        Patch(
            facecolor=COLORS[engine],
            edgecolor="white",
            linewidth=0.3,
            hatch=HATCHES[engine],
            label=DISPLAY[engine],
        )
        for engine in ENGINES
    ]
    figure.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=4,
        frameon=False,
        handlelength=1.5,
        columnspacing=1.6,
        handletextpad=0.45,
    )
    return figure


def _plot_online_panel(
    key: str,
    frame: pd.DataFrame,
    ratio_axis: plt.Axes,
    time_axis: plt.Axes,
    column: int,
) -> None:
    _configure_axis(ratio_axis)
    _configure_axis(time_axis)
    draw_recast_reference_line(ratio_axis, linewidth=1.05)

    x = np.arange(len(frame), dtype=float)
    ratio = frame["ratio"].to_numpy()
    ratio_low = frame["ratio_low"].to_numpy()
    ratio_high = frame["ratio_high"].to_numpy()
    ratio_axis.fill_between(x, ratio_low, ratio_high, color=REVM_C_GREEN, alpha=0.14, linewidth=0, zorder=2)
    ratio_axis.plot(x, ratio, color=REVM_C_GREEN, marker="D", markersize=2.8, markeredgecolor="white", markeredgewidth=0.25, zorder=4)
    for index, value in enumerate(ratio):
        ratio_axis.annotate(
            f"{value:.2f}x",
            (x[index], value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=4.8,
            color="#006A50",
            clip_on=False,
        )
    ratio_axis.set_yscale("log", base=2)
    maximum = float(np.max(ratio_high))
    ratio_ticks = _powers_of_two_ticks(maximum)
    ratio_axis.set_yticks(ratio_ticks)
    ratio_axis.set_yticklabels([f"{int(value)}x" for value in ratio_ticks])
    ratio_axis.set_ylim(0.88, max(2.2, maximum * 1.42))
    ratio_axis.tick_params(axis="x", labelbottom=False, bottom=False)
    if column == 0:
        ratio_axis.set_ylabel("revmc / ReCAST", labelpad=2.0)

    for engine, color, linestyle, marker in [
        ("recast", RECAST_BLUE, "-", "o"),
        ("revmc", REVM_C_GREEN, "--", "s"),
    ]:
        values = frame[engine].to_numpy()
        low = frame[f"{engine}_low"].to_numpy()
        high = frame[f"{engine}_high"].to_numpy()
        time_axis.fill_between(x, low, high, color=color, alpha=0.11, linewidth=0, zorder=2)
        time_axis.plot(x, values, color=color, linestyle=linestyle, marker=marker, markersize=2.6, zorder=4)
    time_axis.set_xticks(x)
    time_axis.set_xticklabels([str(value) for value in frame["N"]])
    time_axis.set_xlabel("Invocations, N", labelpad=1.3)
    time_axis.set_xlim(-0.35, len(frame) - 0.65)
    all_values = np.concatenate([frame["recast_low"].to_numpy(), frame["revmc_high"].to_numpy()])
    lower = max(0.0, float(np.min(all_values)) * 0.88)
    upper = float(np.max(all_values)) * 1.08
    time_axis.set_ylim(lower, upper)
    if column == 0:
        time_axis.set_ylabel("Online total (ms)", labelpad=2.0)


def render_online_composite(root: Path) -> plt.Figure:
    cohorts = load_online_cohorts(root)
    figure, axes = _new_composite(
        figure_height_in=ONLINE_HEIGHT_IN,
        interpanel_hspace=0.10,
        height_ratios=(0.31, 0.69),
        top=0.81,
        bottom=0.17,
    )
    for column, key in enumerate(PANEL_ORDER):
        _plot_online_panel(key, cohorts[key], *axes[column], column)

    handles = [
        Line2D([0], [0], color=RECAST_BLUE, marker="o", linewidth=1.0, markersize=3.0, label="ReCAST"),
        Line2D([0], [0], color=REVM_C_GREEN, marker="s", linestyle="--", linewidth=1.0, markersize=3.0, label="revmc"),
    ]
    figure.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.995),
        ncol=2,
        frameon=False,
        handlelength=2.0,
        columnspacing=2.0,
        handletextpad=0.5,
    )
    return figure


def render_online_single_column_panel(
    root: Path, key: str, *, show_y_labels: bool
) -> plt.Figure:
    """Render one half-column panel of the Figure 8 2x2 layout."""
    if key not in PANEL_ORDER:
        raise ValueError(f"unknown online panel: {key}")
    _set_paper_style()
    figure = plt.figure(
        figsize=(ONLINE_HALF_COLUMN_WIDTH_IN, ONLINE_HALF_COLUMN_HEIGHT_IN)
    )
    grid = figure.add_gridspec(
        2,
        1,
        height_ratios=(0.31, 0.69),
        left=0.24 if show_y_labels else 0.20,
        right=0.985,
        top=0.93,
        bottom=0.20,
        hspace=0.10,
    )
    ratio_axis = figure.add_subplot(grid[0, 0])
    time_axis = figure.add_subplot(grid[1, 0], sharex=ratio_axis)
    ratio_axis.set_gid(f"ratio-{key}")
    time_axis.set_gid(f"time-{key}")
    _plot_online_panel(
        key,
        load_online_cohorts(root)[key],
        ratio_axis,
        time_axis,
        0 if show_y_labels else 1,
    )
    time_axis.set_xlabel("Invocations, N", labelpad=1.0)
    if show_y_labels:
        ratio_axis.set_ylabel("Relative time", labelpad=1.2)
        time_axis.set_ylabel("Time (ms)", labelpad=1.2)
    else:
        ratio_axis.set_ylabel("")
        time_axis.set_ylabel("")
    return figure


def render_online_single_column_legend() -> plt.Figure:
    """Render the shared legend separately so LaTeX controls panel captions."""
    _set_paper_style()
    figure = plt.figure(figsize=(ONLINE_LEGEND_WIDTH_IN, ONLINE_LEGEND_HEIGHT_IN))
    handles = [
        Line2D(
            [0], [0], color=RECAST_BLUE, marker="o", linewidth=1.0,
            markersize=3.0, label="ReCAST"
        ),
        Line2D(
            [0], [0], color=REVM_C_GREEN, marker="s", linestyle="--",
            linewidth=1.0, markersize=3.0, label="revmc"
        ),
    ]
    figure.legend(
        handles=handles,
        loc="center",
        bbox_to_anchor=(0.5, 0.5),
        ncol=2,
        frameon=False,
        handlelength=2.0,
        columnspacing=2.0,
        handletextpad=0.5,
    )
    return figure


def save_online_single_column_panels(root: Path, output_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    for index, key in enumerate(PANEL_ORDER):
        figure = render_online_single_column_panel(
            root, key, show_y_labels=index in {0, 2}
        )
        stem = key.replace("_", "-")
        outputs += _save_figure(figure, output_dir / f"exp2-online-{stem}-panel", top_pad_pt=4.0)
        plt.close(figure)
    legend = render_online_single_column_legend()
    outputs += _save_figure(legend, output_dir / "exp2-online-shared-legend")
    plt.close(legend)
    return outputs


def _save_figure(figure: plt.Figure, base: Path, top_pad_pt: float = 0.0) -> list[Path]:
    outputs: list[Path] = []
    width_in, height_in = figure.get_size_inches()
    bbox = Bbox.from_bounds(0, 0, width_in, height_in + top_pad_pt / 72.0) if top_pad_pt else None
    for suffix, kwargs in [
        (".pdf", {}),
        (".svg", {}),
        (".png", {"dpi": 300}),
    ]:
        path = base.with_suffix(suffix)
        figure.savefig(path, bbox_inches=bbox, pad_inches=0, **kwargs)
        outputs.append(path)
    return outputs


def save_composites(root: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    steady = render_steady_composite(root)
    online = render_online_composite(root)
    outputs = _save_figure(steady, output_dir / "exp2-steady-state-four-panel")
    outputs += _save_figure(online, output_dir / "exp2-online-total-latency-four-panel")
    plt.close(steady)
    plt.close(online)
    outputs += save_online_single_column_panels(root, output_dir)
    return outputs


def _write_provenance(root: Path, output_dir: Path, outputs: Iterable[Path]) -> Path:
    sources = {str(path): _sha256(root / path) for path in [*STEADY_SOURCES.values(), *ONLINE_SOURCES.values()]}
    products = {path.name: _sha256(path) for path in outputs}
    provenance = {
        "figure_width_in": FIGURE_WIDTH_IN,
        "steady_height_in": STEADY_HEIGHT_IN,
        "online_height_in": ONLINE_HEIGHT_IN,
        "online_half_column_width_in": ONLINE_HALF_COLUMN_WIDTH_IN,
        "online_half_column_height_in": ONLINE_HALF_COLUMN_HEIGHT_IN,
        "steady_sources": [str(path) for path in STEADY_SOURCES.values()],
        "online_sources": [str(path) for path in ONLINE_SOURCES.values()],
        "source_sha256": sources,
        "output_sha256": products,
        "statistics_policy": "plot released aggregate CSVs without recomputation",
    }
    path = output_dir / "PROVENANCE.json"
    path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    outputs = save_composites(root, output_dir)
    provenance = _write_provenance(root, output_dir, outputs)
    for output in [*outputs, provenance]:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
