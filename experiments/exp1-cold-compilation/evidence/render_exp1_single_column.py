#!/usr/bin/env python3
"""Render the four panels of Figure 6 from the released Experiment 1 tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Callable, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, NullFormatter
import numpy as np
import pandas as pd



PANEL_WIDTH_IN = 1.62
PANEL_HEIGHT_IN = 1.38
BOOTSTRAP_SEED = 20260810
BLUE = "#4477AA"
MAGENTA = "#AA3377"
INK = "#222222"
GRID = "#D9E2EC"
EQUIVALENCE_FILL = "#DDEFE4"
PHASE_EXPECTED_SHA256 = "67f814108a87896421b89be603bc918f88c27d79009a150e93dc7a37a4ce9737"
PHASE_COLORS = {
    "Recover": "#4C78A8",
    "Admit": "#F2CF5B",
    "Specialize": "#F58518",
    "Backend": "#54A24B",
    "Other / unattributed": "#B8B8B8",
}
EXPECTED_HASHES = {
    "cross-engine/analysis/main/compile-time-data.csv":
        "8ec9e39259e2f828987dcd3443c993ec3e12642ff64752f8ecf389c6804fde79",
    "cross-engine/analysis/main/summary.json":
        "3f3f7255961a4ad58b45983e2ba8467a74e2e999287a3b2877ae0b5fe67f61f0",
    "cross-engine/analysis/scaleout/compile-time-data.csv":
        "520a086b51443f45c3bc5326d379f79b16e1e447dd7c7e030dee79729799b14c",
    "cross-engine/analysis/scaleout/summary.json":
        "7f951f34934f4b1b51746afc8e66e4cb7a9acb8d98ad6319083759b10421c6d2",
    "same-source-ablation/formal-01/analysis/per_contract.csv":
        "f79e5f56b1904faf34fe1e30c13b0d795ff4305d38c91c0c9d40b7a81991d728",
    "same-source-ablation/formal-01/analysis/strata_summary.csv":
        "025d2de6e3e35225054d2c00669fe0ac135841703b8d1920cc9aef320498dd6e",
    "same-source-ablation/formal-01/analysis/summary.json":
        "a27454fde08efb9dfa867d98227ead123a4268d649c430b036eb62c739ed876b",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometric_mean(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0 or np.any(array <= 0):
        raise ValueError("geometric mean requires nonempty positive values")
    return float(np.exp(np.mean(np.log(array))))


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def verify_inputs(root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in EXPECTED_HASHES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"input identity drift for {relative}: {actual} != {expected}"
            )
        observed[relative] = actual
    return observed


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values.astype(float))
    y = np.arange(1, len(x) + 1, dtype=float) / len(x)
    return x, y


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_geomean(
    values: list[float], *, seed: int, samples: int = 2_000
) -> tuple[float, float]:
    generator = random.Random(seed)
    estimates: list[float] = []
    for _ in range(samples):
        sample = [values[generator.randrange(len(values))] for _ in values]
        estimates.append(math.exp(statistics.fmean(math.log(value) for value in sample)))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def rolling_deciles(
    frame: pd.DataFrame, *, seed: int
) -> tuple[list[float], list[float], list[float], list[float]]:
    ordered = frame.sort_values(["bytecode_bytes", "code_hash"], kind="mergesort")
    bucket_count = 10
    x_values: list[float] = []
    estimates: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    for bucket in range(bucket_count):
        start = len(ordered) * bucket // bucket_count
        end = len(ordered) * (bucket + 1) // bucket_count
        group = ordered.iloc[start:end]
        ratios = group["dtvm_over_revmc"].astype(float).tolist()
        x_values.append(float(statistics.median(group["bytecode_bytes"])))
        estimates.append(geometric_mean(ratios))
        low, high = bootstrap_geomean(ratios, seed=seed + bucket)
        lower.append(low)
        upper.append(high)
    return x_values, estimates, lower, upper


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
            "font.size": 5.8,
            "axes.labelsize": 6.0,
            "xtick.labelsize": 5.2,
            "ytick.labelsize": 5.2,
            "legend.fontsize": 5.2,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.55,
            "grid.color": GRID,
            "grid.linewidth": 0.35,
            "grid.alpha": 0.72,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "recast-exp1-single-column-20260820",
        }
    )


def style_axis(axis: plt.Axes, *, grid_axis: str = "both") -> None:
    axis.grid(True, axis=grid_axis, which="major", zorder=0)
    axis.tick_params(length=2.0, width=0.5, pad=1.2)


def draw_distribution(axis: plt.Axes, frame: pd.DataFrame) -> None:
    for label, column, color, linestyle in [
        ("ReCAST", "dtvm_median_ns", BLUE, "-"),
        ("revmc-JIT", "revmc_median_ns", MAGENTA, (0, (4, 2))),
    ]:
        values_ms = frame[column].to_numpy(dtype=float) / 1e6
        x_values, y_values = ecdf(values_ms)
        axis.step(
            x_values,
            y_values,
            where="post",
            color=color,
            linestyle=linestyle,
            linewidth=0.95,
            label=label,
            zorder=3,
        )
        axis.scatter(
            [statistics.median(values_ms)],
            [0.5],
            s=8,
            color=color,
            edgecolor=INK,
            linewidth=0.25,
            zorder=5,
        )
        axis.scatter(
            [percentile(values_ms.tolist(), 0.95)],
            [0.95],
            s=10,
            marker="D",
            color=color,
            edgecolor=INK,
            linewidth=0.25,
            zorder=5,
        )
    axis.set_xscale("log")
    axis.set_xlim(0.8, 12_000)
    axis.set_ylim(0.0, 1.02)
    axis.set_xlabel("Compile-to-callable (ms)")
    axis.set_ylabel("ECDF")
    style_axis(axis)
    axis.legend(frameon=False, loc="lower right", handlelength=1.8, borderaxespad=0.2)


def draw_ratio_size(
    axis: plt.Axes, frame: pd.DataFrame, summary: dict[str, Any]
) -> None:
    ratios = frame["dtvm_over_revmc"].to_numpy(dtype=float)
    sizes = frame["bytecode_bytes"].to_numpy(dtype=float)
    axis.scatter(
        sizes,
        ratios,
        s=2.5,
        color=BLUE,
        edgecolor="none",
        alpha=0.28,
        zorder=2,
    )
    x_roll, estimate_roll, lower_roll, upper_roll = rolling_deciles(
        frame, seed=BOOTSTRAP_SEED + 500
    )
    axis.fill_between(
        x_roll,
        lower_roll,
        upper_roll,
        color="#BBBBBB",
        alpha=0.30,
        linewidth=0,
        zorder=1,
    )
    axis.plot(x_roll, estimate_roll, color=INK, linewidth=0.8, zorder=4)
    axis.axhline(1.0, color=INK, linestyle="--", linewidth=0.6, zorder=3)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlim(min(sizes) * 0.82, max(sizes) * 1.35)
    axis.set_ylim(min(ratios) / 1.8, max(ratios) * 1.8)
    axis.set_xlabel("Runtime bytecode (bytes)")
    axis.set_ylabel("ReCAST / revmc")
    style_axis(axis)
    axis.xaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1))
    axis.xaxis.set_minor_formatter(NullFormatter())
    axis.text(
        0.03,
        0.03,
        (
            f"GM {float(summary['geometric_mean_ratio']):.3f}\n"
            f"95% CI [{float(summary['ci95'][0]):.3f}, {float(summary['ci95'][1]):.3f}]"
        ),
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.0,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 0.7},
        zorder=6,
    )


def draw_rcs_forest(axis: plt.Axes, strata: pd.DataFrame) -> None:
    order = [
        ("all", "all", "Overall"),
        ("size_quartile", "Q1", "Size Q1"),
        ("size_quartile", "Q2", "Size Q2"),
        ("size_quartile", "Q3", "Size Q3"),
        ("size_quartile", "Q4", "Size Q4"),
        ("cfg_group", "High", "CFG High"),
        ("cfg_group", "Low", "CFG Low"),
        ("cfg_group", "Medium", "CFG Med."),
    ]
    rows: list[tuple[str, float, float, float]] = []
    for dimension, stratum, label in order:
        match = strata.loc[
            (strata["dimension"] == dimension) & (strata["stratum"] == stratum)
        ]
        if len(match) != 1:
            raise RuntimeError(f"missing stratum {dimension}/{stratum}")
        row = match.iloc[0]
        rows.append(
            (
                label,
                float(row["geomean_ratio"]),
                float(row["ci95_low"]),
                float(row["ci95_high"]),
            )
        )
    y_values = np.arange(len(rows), dtype=float)
    point = np.asarray([row[1] for row in rows])
    low = np.asarray([row[2] for row in rows])
    high = np.asarray([row[3] for row in rows])
    axis.axvspan(0.97, 1.03, color=EQUIVALENCE_FILL, alpha=0.90, zorder=0)
    axis.axvline(1.0, color="#555555", linestyle="--", linewidth=0.6, zorder=2)
    axis.errorbar(
        point,
        y_values,
        xerr=np.vstack([point - low, high - point]),
        fmt="o",
        color=BLUE,
        ecolor=BLUE,
        markersize=2.7,
        linewidth=0.65,
        capsize=1.4,
        markeredgecolor=INK,
        markeredgewidth=0.2,
        zorder=4,
    )
    axis.set_yticks(y_values, [row[0] for row in rows])
    axis.invert_yaxis()
    axis.set_xlim(0.932, 1.042)
    axis.set_xticks([0.94, 0.97, 1.00, 1.03])
    axis.set_xlabel("Full ReCAST / ReCAST-disabled\ncompile-time ratio", fontsize=5.2, labelpad=1.0)
    style_axis(axis, grid_axis="x")
    axis.text(
        0.97,
        0.05,
        r"equivalence $\pm$3%",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=4.9,
        color="#444444",
    )


def draw_phase_breakdown(axis: plt.Axes, phases: pd.DataFrame) -> None:
    indexed = phases.set_index("category")
    shares = {
        name: float(indexed.loc[name, "code_balanced_mean_share"]) * 100.0
        for name in PHASE_COLORS
    }
    if not math.isclose(sum(shares.values()), 100.0, rel_tol=0.0, abs_tol=0.02):
        raise RuntimeError("phase shares do not sum to 100%")
    proof_names = ["Recover", "Admit", "Specialize"]
    proof_total = sum(shares[name] for name in proof_names)
    backend = shares["Backend"]
    other = shares["Other / unattributed"]

    overall_y = 0.70
    overall_height = 0.17
    left = 0.0
    for share, color in [
        (proof_total, BLUE),
        (backend, PHASE_COLORS["Backend"]),
        (other, PHASE_COLORS["Other / unattributed"]),
    ]:
        axis.barh(
            [overall_y],
            [share],
            left=[left],
            height=overall_height,
            color=color,
            edgecolor="white",
            linewidth=0.25,
            zorder=3,
        )
        left += share
    axis.text(
        proof_total + backend / 2.0,
        overall_y,
        f"Backend\n{backend:.2f}%",
        ha="center",
        va="center",
        fontsize=5.5,
        color="white",
        fontweight="semibold",
    )
    axis.annotate(
        f"Proof {proof_total:.2f}%",
        xy=(proof_total / 2.0, overall_y + overall_height / 2.0),
        xytext=(5.5, 0.91),
        ha="left",
        va="center",
        fontsize=5.0,
        arrowprops={"arrowstyle": "-", "color": BLUE, "lw": 0.45},
    )
    axis.annotate(
        f"Other {other:.2f}%",
        xy=(proof_total + backend + other / 2.0, overall_y + overall_height / 2.0),
        xytext=(95.0, 0.91),
        ha="right",
        va="center",
        fontsize=5.0,
        arrowprops={"arrowstyle": "-", "color": "#777777", "lw": 0.45},
    )

    detail_y = 0.24
    detail_height = 0.18
    proof_left = 0.0
    for name in proof_names:
        normalized_share = shares[name] / proof_total * 100.0
        axis.barh(
            [detail_y],
            [normalized_share],
            left=[proof_left],
            height=detail_height,
            color=PHASE_COLORS[name],
            edgecolor="white",
            linewidth=0.25,
            zorder=3,
        )
        proof_left += normalized_share
    recover_normalized = shares["Recover"] / proof_total * 100.0
    axis.text(
        recover_normalized / 2.0,
        detail_y,
        f"Recover\n{shares['Recover']:.2f}%",
        ha="center",
        va="center",
        fontsize=5.2,
        color="white",
        fontweight="semibold",
    )
    axis.text(
        recover_normalized + (100.0 - recover_normalized) / 2.0,
        detail_y,
        f"Specialize\n{shares['Specialize']:.2f}%",
        ha="center",
        va="center",
        fontsize=5.2,
        color=INK,
        fontweight="semibold",
    )
    axis.axvline(
        recover_normalized,
        ymin=0.19,
        ymax=0.29,
        color=PHASE_COLORS["Admit"],
        linewidth=0.9,
        zorder=6,
    )
    axis.text(
        50.0,
        0.44,
        f"Proof-stage detail ({proof_total:.2f}% of total)",
        ha="center",
        va="center",
        fontsize=5.0,
        color="#444444",
    )
    axis.text(
        recover_normalized,
        0.075,
        "Admit <0.01%",
        ha="center",
        va="center",
        fontsize=4.8,
        color="#555555",
    )
    axis.plot(
        [0.0, 0.0],
        [overall_y - overall_height / 2.0, detail_y + detail_height / 2.0],
        color="#9AA7B2",
        linestyle=(0, (2, 2)),
        linewidth=0.4,
    )
    axis.plot(
        [proof_total, 100.0],
        [overall_y - overall_height / 2.0, detail_y + detail_height / 2.0],
        color="#9AA7B2",
        linestyle=(0, (2, 2)),
        linewidth=0.4,
    )
    axis.set_xlim(0.0, 100.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)


def save_panel(
    output_dir: Path,
    name: str,
    draw: Callable[[plt.Axes], None],
    *,
    axis_bounds: tuple[float, float, float, float],
) -> tuple[dict[str, float], dict[str, str]]:
    figure = plt.figure(figsize=(PANEL_WIDTH_IN, PANEL_HEIGHT_IN))
    axis = figure.add_axes(axis_bounds)
    draw(axis)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / name
    figure.savefig(
        stem.with_suffix(".pdf"),
        metadata={
            "Creator": "render_exp1_single_column.py",
            "Producer": "Matplotlib",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    figure.savefig(
        stem.with_suffix(".svg"),
        metadata={"Creator": "render_exp1_single_column.py", "Date": None},
    )
    figure.savefig(
        stem.with_suffix(".png"),
        dpi=600,
        metadata={"Software": "render_exp1_single_column.py"},
    )
    geometry = {
        "left": axis_bounds[0],
        "bottom": axis_bounds[1],
        "width": axis_bounds[2],
        "height": axis_bounds[3],
        "center_x": axis_bounds[0] + axis_bounds[2] / 2.0,
    }
    plt.close(figure)
    hashes = {
        path.name: sha256(path)
        for path in [stem.with_suffix(".pdf"), stem.with_suffix(".svg"), stem.with_suffix(".png")]
    }
    return geometry, hashes


def render(root: Path, output_dir: Path) -> dict[str, Any]:
    input_hashes = verify_inputs(root)
    main = pd.read_csv(root / "cross-engine/analysis/main/compile-time-data.csv")
    main_summary = load_json(root / "cross-engine/analysis/main/summary.json")
    strata = pd.read_csv(root / "same-source-ablation/formal-01/analysis/strata_summary.csv")
    phase_path = root / "same-source-ablation/formal-01/analysis/phase_category_summary.csv"
    phase_hash = sha256(phase_path)
    if phase_hash != PHASE_EXPECTED_SHA256:
        raise RuntimeError(f"phase input identity drift: {phase_hash}")
    input_hashes[str(phase_path.relative_to(root)).replace("\\", "/")] = phase_hash
    phases = pd.read_csv(phase_path)
    if len(main) != 1_200:
        raise RuntimeError(f"unexpected Main cohort size: {len(main)}")

    configure_style()
    panels = [
        (
            "exp1-a-main-distribution",
            lambda axis: draw_distribution(axis, main),
            (0.22, 0.20, 0.74, 0.76),
        ),
        (
            "exp1-b-ratio-size",
            lambda axis: draw_ratio_size(axis, main, main_summary),
            (0.22, 0.20, 0.74, 0.76),
        ),
        (
            "exp1-c-same-source-cost",
            lambda axis: draw_rcs_forest(axis, strata),
            (0.25, 0.20, 0.71, 0.76),
        ),
        (
            "exp1-d-compile-breakdown",
            lambda axis: draw_phase_breakdown(axis, phases),
            (0.18, 0.10, 0.78, 0.86),
        ),
    ]
    geometry: dict[str, dict[str, float]] = {}
    output_hashes: dict[str, str] = {}
    for name, draw, bounds in panels:
        panel_geometry, panel_hashes = save_panel(
            output_dir, name, draw, axis_bounds=bounds
        )
        geometry[name] = panel_geometry
        output_hashes.update(panel_hashes)

    provenance = {
        "schema_version": 1,
        "figure": "Figure 6, panels (a)-(d)",
        "panel_size_in": {"width": PANEL_WIDTH_IN, "height": PANEL_HEIGHT_IN},
        "panels": geometry,
        "cohorts": {"main": len(main)},
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
    }
    provenance_path = output_dir / "exp1-single-column.provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "figures" / "single-column",
    )
    arguments = parser.parse_args()
    provenance = render(arguments.root.resolve(), arguments.output_dir.resolve())
    print(json.dumps(provenance, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
