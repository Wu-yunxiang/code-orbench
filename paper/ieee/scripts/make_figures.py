#!/usr/bin/env python3
"""Generate paper figures from the fixed Code-ORBench metrics."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


OVERALL = [
    ("Qwen3-14B", 4.59),
    ("Claude Haiku 4.5", 15.82),
    ("Gemini 3 Flash", 17.86),
    ("GPT-4o", 20.66),
    ("Qwen3-30B", 39.29),
    ("Qwen3-235B Inst.", 76.28),
    ("Qwen3-Coder+", 77.30),
    ("Qwen3-235B Think", 77.55),
    ("GPT-4o-mini", 84.69),
]


CATEGORIES = [
    "Network",
    "Ransom.",
    "Spyware",
    "Trojan",
    "Viruses",
    "Worms",
]


MODEL_ORDER = [
    "Qwen3-14B",
    "Claude Haiku 4.5",
    "Gemini 3 Flash",
    "GPT-4o",
    "Qwen3-30B",
    "Qwen3-235B Inst.",
    "Qwen3-Coder+",
    "Qwen3-235B Think",
    "GPT-4o-mini",
]


CATEGORY_ORR = {
    "Claude Haiku 4.5": [14.94, 18.52, 12.50, 20.00, 15.00, 19.44],
    "Gemini 3 Flash": [25.29, 55.56, 13.39, 2.86, 18.33, 13.89],
    "GPT-4o": [29.89, 11.11, 18.75, 41.43, 0.00, 5.56],
    "GPT-4o-mini": [93.10, 85.19, 86.61, 100.00, 53.33, 80.56],
    "Qwen3-14B": [4.60, 3.70, 5.36, 7.14, 1.67, 2.78],
    "Qwen3-235B Inst.": [86.21, 74.07, 81.25, 100.00, 45.00, 44.44],
    "Qwen3-235B Think": [90.80, 77.78, 79.46, 100.00, 48.33, 44.44],
    "Qwen3-30B": [18.39, 59.26, 37.50, 94.29, 18.33, 8.33],
    "Qwen3-Coder+": [73.56, 88.89, 83.04, 70.00, 70.00, 86.11],
}


def save_overall_orr() -> None:
    labels = [x[0] for x in OVERALL]
    values = [x[1] for x in OVERALL]
    colors = ["#4C78A8" if v < 50 else "#F58518" for v in values]

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Over-refusal rate (%)")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.45)
    for idx, value in enumerate(values):
        ax.text(value + 1.2, idx, f"{value:.1f}%", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Overall ORR on Code-ORBench")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "overall_orr.pdf")
    fig.savefig(FIG_DIR / "overall_orr.png", dpi=220)
    plt.close(fig)


def save_category_heatmap() -> None:
    data = np.array([CATEGORY_ORR[m] for m in MODEL_ORDER])

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    im = ax.imshow(data, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(CATEGORIES)), CATEGORIES, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(MODEL_ORDER)), MODEL_ORDER)
    ax.set_title("Category-level ORR (%)")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            color = "white" if value > 65 else "black"
            ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=7, color=color)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("ORR (%)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "category_heatmap.pdf")
    fig.savefig(FIG_DIR / "category_heatmap.png", dpi=220)
    plt.close(fig)


def main() -> None:
    save_overall_orr()
    save_category_heatmap()
    print(f"Wrote figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
