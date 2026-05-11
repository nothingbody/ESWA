from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
OUT = ROOT / "docs" / "eswa_figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    output_path = OUT / name
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    if output_path.suffix.lower() == ".png":
        with Image.open(output_path) as image:
            image.convert("RGB").save(output_path, dpi=(300, 300))
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def box(ax, x: float, y: float, w: float, h: float, text: str, fill: str = "#F7FAFC") -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.025",
        linewidth=1.2,
        edgecolor="#334155",
        facecolor=fill,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, color="#111827", wrap=True)


def arrow(ax, x1: float, y1: float, x2: float, y2: float, label: str | None = None) -> None:
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.1,
            color="#475569",
        )
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.025, label, ha="center", va="bottom", fontsize=8, color="#334155")


def framework_figure() -> None:
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    layers = [
        (0.08, 0.78, "Data and task layer", "Solomon, Homberger,\nLi & Lim task abstraction", "#F8FAFC"),
        (0.08, 0.64, "Fast construction layer", "nearest, greedy,\nregret and pair drafts", "#E0F2FE"),
        (0.08, 0.50, "Slow verification layer", "process verifier,\ntyped diagnostic records", "#FEF3C7"),
        (0.08, 0.36, "Reflection repair layer", "repair insertion, pair repair,\nroute merge, route elimination", "#DCFCE7"),
        (0.08, 0.22, "Tree-of-Routes selection", "multi-start ALNS,\nfeasible-first lexicographic policy", "#EDE9FE"),
        (0.08, 0.08, "Explanation output layer", "objective tuple,\nviolation-free certificate", "#F8FAFC"),
    ]
    for x, y, title, detail, fill in layers:
        box(ax, x, y, 0.20, 0.09, title, fill)
        box(ax, 0.36, y, 0.48, 0.09, detail, fill)
        arrow(ax, x + 0.20, y + 0.045, 0.36, y + 0.045)
    for idx in range(len(layers) - 1):
        arrow(ax, 0.60, layers[idx][1], 0.60, layers[idx + 1][1] + 0.09)
    arrow(ax, 0.84, 0.405, 0.84, 0.545, "diagnostic feedback")
    arrow(ax, 0.84, 0.265, 0.84, 0.405)
    save(fig, "Figure_1_Framework.png")


def verifier_figure() -> None:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    box(ax, 0.04, 0.42, 0.16, 0.16, "Input:\ncandidate route\nsolution", "#E0F2FE")
    verifier = FancyBboxPatch(
        (0.27, 0.13),
        0.32,
        0.74,
        boxstyle="round,pad=0.025,rounding_size=0.025",
        linewidth=1.2,
        edgecolor="#334155",
        facecolor="#F8FAFC",
    )
    ax.add_patch(verifier)
    ax.text(
        0.43,
        0.82,
        "Independent verifier /\ninference engine",
        ha="center",
        va="center",
        fontsize=9,
        color="#111827",
    )
    checks = [
        (0.31, 0.68, "Capacity"),
        (0.31, 0.56, "Time windows"),
        (0.31, 0.44, "Service-time\npropagation"),
        (0.31, 0.32, "Duplicate /\nunserved"),
        (0.31, 0.20, "Precedence /\nsame-vehicle"),
    ]
    for x, y, text in checks:
        box(ax, x, y, 0.24, 0.07, text)

    box(ax, 0.66, 0.62, 0.16, 0.12, "Typed violation\nrecords", "#FEF3C7")
    box(ax, 0.66, 0.42, 0.16, 0.12, "Objective tuple\n(K, D)", "#FEF3C7")
    box(ax, 0.66, 0.22, 0.16, 0.12, "Feasibility\ncertificate", "#FEF3C7")
    box(ax, 0.86, 0.41, 0.10, 0.18, "Output to\nrepair and\nselection", "#DCFCE7")

    arrow(ax, 0.20, 0.50, 0.27, 0.50)
    arrow(ax, 0.59, 0.50, 0.66, 0.68)
    arrow(ax, 0.59, 0.50, 0.66, 0.48)
    arrow(ax, 0.59, 0.50, 0.66, 0.28)
    arrow(ax, 0.82, 0.68, 0.86, 0.50)
    arrow(ax, 0.82, 0.48, 0.86, 0.50)
    arrow(ax, 0.82, 0.28, 0.86, 0.50)
    save(fig, "Figure_2_Verification.png")


def bar(
    values: list[float],
    labels: list[str],
    ylabel: str,
    name: str,
    colors: list[str] | None = None,
    annotation: str | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    if colors is None:
        colors = ["#2F6F73", "#8C6A3F", "#6F5B8C", "#4D7C3B"][: len(labels)]
    bars = ax.bar(labels, values, color=colors, edgecolor="#1F2937", linewidth=0.6)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(values) * 1.28)
    for item in bars:
        ax.text(
            item.get_x() + item.get_width() / 2,
            item.get_height() + max(values) * 0.025,
            f"{item.get_height():.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#111827",
        )
    if annotation:
        ax.text(
            0.98,
            0.96,
            annotation,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#CBD5E1", "alpha": 0.95},
        )
    fig.tight_layout()
    save(fig, name)


def solomon_gap_figure() -> None:
    stage = next(row for row in read_rows(TABLES / "solomon_stage1_gap_summary.csv") if row["method"] == "greedy_insertion")
    basic = next(row for row in read_rows(TABLES / "solomon_alns_all_gap_summary.csv") if row["method"] == "greedy_insertion+basic_alns")
    advanced = read_rows(TABLES / "advanced_alns_all_gap_summary.csv")[0]
    bar(
        [float(stage["avg_vehicle_gap"]), float(basic["avg_vehicle_gap"]), float(advanced["avg_vehicle_gap"])],
        ["Greedy\nbaseline", "Basic\nALNS", "Advanced\nmulti-start ALNS"],
        "Average vehicle gap",
        "Figure_3_Solomon_Gap.png",
        annotation="Advanced ALNS reduces\ngreedy gap by 69.51%",
    )


def lilim_gap_figure() -> None:
    rows = read_rows(TABLES / "li_lim_stage1_gap_summary.csv")
    base = next(row for row in rows if row["method"] == "greedy_pair_insertion")
    pair = next(row for row in rows if row["method"] == "greedy_pair_insertion+pair_alns")
    bar(
        [float(base["avg_vehicle_gap"]), float(pair["avg_vehicle_gap"])],
        ["Pair insertion\nbaseline", "Pair-aware\nmulti-start ALNS"],
        "Average vehicle gap",
        "Figure_4_LiLim_Gap.png",
        ["#2F6F73", "#6F5B8C"],
        annotation="Pair-aware ALNS reduces\ngap by 66.67%",
    )


def ablation_figure() -> None:
    rows = read_rows(TABLES / "solomon_ablation_all_updated_gap_summary.csv")
    nn_rows = [row for row in rows if row["generator"] == "nearest_neighbor"]
    variants = ["fast_only", "fast_repair_merge", "fast_repair_merge_elim", "full_ftv"]
    lookup = {row["variant"]: row for row in nn_rows}
    vehicle_gaps = [float(lookup[item]["avg_vehicle_gap"]) for item in variants]
    feasible = [float(lookup[item]["feasible_rate"]) for item in variants]

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    labels = ["Fast only", "Repair+merge", "+route elim.", "Full framework"]
    axes[0].bar(labels, vehicle_gaps, color="#2F6F73", edgecolor="#1F2937", linewidth=0.6)
    axes[0].set_ylabel("Average vehicle gap")
    axes[1].bar(labels, feasible, color="#6F5B8C", edgecolor="#1F2937", linewidth=0.6)
    axes[1].set_ylabel("Feasible rate")
    axes[0].set_ylim(0, max(vehicle_gaps) * 1.25)
    axes[1].set_ylim(0, 1.12)
    for ax, values in zip(axes, [vehicle_gaps, feasible]):
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", rotation=15)
        for patch, value in zip(ax.patches, values):
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                patch.get_height() + max(values) * 0.025,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
    fig.tight_layout()
    save(fig, "Figure_5_Ablation.png")


def main() -> None:
    framework_figure()
    verifier_figure()
    solomon_gap_figure()
    lilim_gap_figure()
    ablation_figure()
    print(OUT)


if __name__ == "__main__":
    main()
