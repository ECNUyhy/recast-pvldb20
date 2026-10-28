#!/usr/bin/env python3
"""Render Figure 9 (cumulative time for the 1,000-block mainnet replay) from exp3-mainnet-replay.tsv."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import median

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
DATA = HERE / "exp3-mainnet-replay.tsv"
OUT_BASE = HERE / "exp3-mainnet-replay"

SERIES = {
    "ReCAST": "recast_ms",
    "DTVM JIT": "dtvm_jit_ms",
    "DTVM interpreter": "dtvm_interpreter_ms",
    "evmone Baseline": "evmone_baseline_ms",
    "evmone Advanced": "evmone_advanced_ms",
    "Geth": "geth_ms",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


with DATA.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t"))

if len(rows) != 1000:
    raise ValueError(f"expected 1000 replay rows, found {len(rows)}")

blocks = [int(row["block"]) for row in rows]
if blocks != list(range(blocks[0], blocks[0] + 1000)):
    raise ValueError("replay window is not a contiguous 1,000-block interval")

latency_ms = {
    name: [float(row[column]) for row in rows]
    for name, column in SERIES.items()
}
for name, values in latency_ms.items():
    if len(values) != 1000 or any(value <= 0 for value in values):
        raise ValueError(f"invalid per-block timing series: {name}")


def cumulative_seconds(values_ms: list[float]) -> list[float]:
    total = 0.0
    output = [0.0]
    for value in values_ms:
        total += value / 1000.0
        output.append(total)
    return output


plot_x = list(range(0, 1001))
cumulative_s = {
    name: cumulative_seconds(values) for name, values in latency_ms.items()
}

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 7.15,
        "axes.labelsize": 7.7,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "legend.fontsize": 5.75,
        "axes.linewidth": 0.65,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
)

# Keep the plot at native single-column width while using the shallower
# aspect ratio common to PVLDB performance figures.  This preserves the
# publication-size type rather than shrinking the entire figure in LaTeX.
fig, ax = plt.subplots(figsize=(3.33, 1.42), constrained_layout=False)

styles = {
    "ReCAST": {
        "color": "#0072B2", "lw": 1.28, "ls": "-", "marker": "o", "zorder": 6,
    },
    "DTVM JIT": {
        "color": "#332288", "lw": 1.05, "ls": (0, (5.0, 1.4)), "marker": "h", "zorder": 5,
    },
    "DTVM interpreter": {
        "color": "#56B4E9", "lw": 1.05, "ls": "--", "marker": "s", "zorder": 5,
    },
    "evmone Baseline": {
        "color": "#009E73", "lw": 1.05, "ls": "-.", "marker": "^", "zorder": 4,
    },
    "evmone Advanced": {
        "color": "#CC79A7", "lw": 1.05, "ls": ":", "marker": "D", "zorder": 3,
    },
    "Geth": {
        "color": "#D55E00", "lw": 1.12, "ls": "-", "marker": "v", "zorder": 2,
    },
}

for name in SERIES:
    style = styles[name]
    ax.plot(
        plot_x,
        cumulative_s[name],
        label="Geth (client-level)" if name == "Geth" else name,
        color=style["color"],
        linewidth=style["lw"],
        linestyle=style["ls"],
        marker=style["marker"],
        markevery=100,
        markersize=1.65,
        markerfacecolor="white",
        markeredgewidth=0.52,
        solid_capstyle="round",
        zorder=style["zorder"],
    )

# Preserve the true zero origin and every connected cumulative sample while
# resolving the four lower-time curves. Above 10 seconds the scale is logarithmic.
ax.set_yscale("symlog", linthresh=10, linscale=1.0, base=10)
ax.set_ylim(0, 1600)
ax.set_yticks([0, 10, 30, 100, 300, 1000])
ax.set_yticklabels(["0", "10", "30", "100", "300", "1000"])
ax.set_xlim(0, 1030)
ax.set_xticks([0, 250, 500, 750, 1000])
ax.set_xlabel("Consecutive mainnet blocks")
ax.set_ylabel("Cumulative time (s; symlog)")
ax.grid(axis="y", which="major", color="#D3D7DB", lw=0.55, alpha=0.85)
ax.grid(axis="x", which="major", color="#E7E9EB", lw=0.45, alpha=0.70)
ax.tick_params(which="both", direction="out", length=2.3, width=0.55, pad=1.5)
ax.spines["right"].set_visible(False)
ax.spines["top"].set_visible(False)

handles, labels = ax.get_legend_handles_labels()
legend = fig.legend(
    handles,
    labels,
    loc="upper center",
    bbox_to_anchor=(0.58, 0.995),
    ncol=3,
    frameon=False,
    handlelength=1.65,
    columnspacing=0.70,
    handletextpad=0.30,
    borderaxespad=0.0,
    labelspacing=0.28,
)
for line in legend.get_lines():
    line.set_linewidth(1.25)

fig.subplots_adjust(left=0.175, right=0.99, bottom=0.24, top=0.70)

for suffix in ("pdf", "svg", "png"):
    kwargs = {"bbox_inches": "tight", "pad_inches": 0.015}
    if suffix == "png":
        kwargs["dpi"] = 450
    fig.savefig(OUT_BASE.with_suffix(f".{suffix}"), **kwargs)
plt.close(fig)

summary = {
    "schema": "recast-mainnet-replay-figure-v5",
    "source": DATA.name,
    "source_sha256": sha256(DATA),
    "block_count": len(rows),
    "first_block": blocks[0],
    "last_block": blocks[-1],
    "series_columns": SERIES,
    "campaign_groups": {
        "S": "sealed campaign, 2026-08-29",
        "I": "DTVM interpreter leg, 2026-08-30",
        "N": "paired evmone Baseline/Advanced leg, 2026-08-30",
        "DTVM JIT": "DTVM baseline (three consumer families disabled), 2026-10-26, same replay harness",
    },
    "timing_boundary": {
        "ReCAST": "native EVM block execution from executable-bytecode handoff to engine return",
        "DTVM JIT": "reth subject execution with the DTVM multipass JIT in the DTVM baseline configuration",
        "DTVM interpreter": "reth subject execution with the DTVM interpreter; same harness, corpus, and cache policy as the DTVM JIT",
        "evmone Baseline": "reth subject execution with evmone default Baseline executor",
        "evmone Advanced": "reth subject execution with evmone opt-in Advanced executor",
        "Geth": "full-client execution",
    },
    "median_ms": {name: median(values) for name, values in latency_ms.items()},
    "total_seconds": {name: values[-1] for name, values in cumulative_s.items()},
    "relative_to_recast_total": {
        name: values[-1] / cumulative_s["ReCAST"][-1]
        for name, values in cumulative_s.items()
        if name != "ReCAST"
    },
    "plot": "cumulative execution time from block 0 through block 1000; continuous symlog y-axis is linear from 0 to 10 seconds and logarithmic above 10 seconds; no smoothing or block exclusions",
    "display_markers": "every 100 blocks; curves retain all 1000 per-block measurements",
    "axis_scale": "symlog with linthresh=10 seconds, linscale=1.0, and base=10; tick labels remain in seconds",
}
(OUT_BASE.with_suffix(".provenance.json")).write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)

print(json.dumps(summary, indent=2))
