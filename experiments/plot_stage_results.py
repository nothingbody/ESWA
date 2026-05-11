from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def bar_chart(rows: list[dict[str, str]], x_key: str, y_key: str, title: str, output: Path) -> None:
    labels = [row[x_key] for row in rows]
    values = [float(row[y_key]) for row in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    colors = ["#2F6F73", "#8C6A3F", "#6F5B8C", "#4D7C3B", "#9A4D4D"][: len(labels)]
    ax.bar(labels, values, color=colors)
    ax.set_title(title)
    ax.set_ylabel(y_key.replace("_", " "))
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def grouped_ablation(rows: list[dict[str, str]], output: Path) -> None:
    variants = ["fast_only", "fast_repair", "fast_repair_merge", "full_ftv"]
    generators = sorted(set(row["generator"] for row in rows))
    lookup = {(row["generator"], row["variant"]): row for row in rows}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), dpi=160)
    width = 0.22
    x = list(range(len(variants)))
    colors = {"greedy_insertion": "#2F6F73", "nearest_neighbor": "#8C6A3F", "regret_insertion": "#6F5B8C"}
    for offset, generator in enumerate(generators):
        shift = (offset - (len(generators) - 1) / 2) * width
        vehicles = [float(lookup[(generator, variant)]["avg_vehicles"]) for variant in variants]
        feasible = [float(lookup[(generator, variant)]["feasible_rate"]) for variant in variants]
        axes[0].bar([item + shift for item in x], vehicles, width=width, label=generator, color=colors.get(generator))
        axes[1].bar([item + shift for item in x], feasible, width=width, label=generator, color=colors.get(generator))
    for ax, ylabel in zip(axes, ["Average vehicles", "Feasible rate"]):
        ax.set_xticks(x)
        ax.set_xticklabels(variants, rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_title("Ablation: vehicle count")
    axes[1].set_title("Ablation: feasibility")
    axes[1].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def gap_chart(rows: list[dict[str, str]], title: str, output: Path) -> None:
    labels = [row["method"] for row in rows]
    values = [float(row["avg_vehicle_gap"]) for row in rows]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    ax.bar(labels, values, color=["#2F6F73", "#8C6A3F", "#6F5B8C", "#4D7C3B"][: len(labels)])
    ax.axhline(0, color="#222222", linewidth=0.8)
    ax.set_title(title)
    ax.set_ylabel("Average vehicle gap")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create stage result figures.")
    parser.add_argument("--tables", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures", type=Path, default=Path("results/figures"))
    args = parser.parse_args()

    solomon = read_rows(args.tables / "solomon_stage1_summary.csv")
    homberger = read_rows(args.tables / "homberger_200_400_summary.csv")
    li_lim_summary = args.tables / "li_lim_stage1_all_summary.csv"
    if not li_lim_summary.exists():
        li_lim_summary = args.tables / "li_lim_stage1_summary.csv"
    li_lim = read_rows(li_lim_summary)
    ablation = read_rows(args.tables / "solomon_ablation_summary.csv")

    bar_chart(solomon, "method", "avg_vehicles", "Solomon VRPTW: average vehicles", args.figures / "figure_solomon_avg_vehicles.png")
    bar_chart(solomon, "method", "avg_distance", "Solomon VRPTW: average distance", args.figures / "figure_solomon_avg_distance.png")
    bar_chart(homberger, "method", "avg_vehicles", "Homberger 200/400: average vehicles", args.figures / "figure_homberger_avg_vehicles.png")
    bar_chart(li_lim, "method", "avg_vehicles", "Li & Lim PDPTW: average vehicles", args.figures / "figure_li_lim_avg_vehicles.png")
    grouped_ablation(ablation, args.figures / "figure_ablation_summary.png")

    gap_files = [
        ("solomon_stage1_gap_summary.csv", "Solomon VRPTW: average vehicle gap", "figure_solomon_vehicle_gap.png"),
        ("homberger_200_400_gap_summary.csv", "Homberger 200/400: average vehicle gap", "figure_homberger_vehicle_gap.png"),
        ("li_lim_stage1_gap_summary.csv", "Li & Lim PDPTW: average vehicle gap", "figure_li_lim_vehicle_gap.png"),
    ]
    for file_name, title, figure_name in gap_files:
        path = args.tables / file_name
        if path.exists():
            gap_chart(read_rows(path), title, args.figures / figure_name)


if __name__ == "__main__":
    main()
