#!/usr/bin/env python3
"""Generate ACL paper figures from finalized Code-ORBench results."""

from __future__ import annotations

import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
FIG_DIR = ROOT / "paper" / "acl" / "latex" / "figures"
ORR_DIRS = [
    ROOT / "dataset" / "full_all" / "05_judged_refusal_intent",
    ROOT / "dataset" / "full_all" / "05_judged_expanded_refusal_intent",
]
TOXIC_CSV = ROOT / "dataset" / "toxic_aligned" / "07_orr_toxic_comparison_refusal_intent.csv"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ORR_REPORT = load_module("phase06_report_metrics", ROOT / "evaluator" / "06_report_metrics.py")
TOXIC_REPORT = load_module("toxic_report", ROOT / "evaluator" / "toxic_report.py")


def pct_float(text: str) -> float:
    return float(str(text).rstrip("%"))


def family(model: str) -> str:
    return TOXIC_REPORT.model_family(model)


def display(model: str) -> str:
    return TOXIC_REPORT.display_model(model)


def load_orr_rows() -> list[dict]:
    rows: dict[str, dict] = {}
    for directory in ORR_DIRS:
        for path in sorted(directory.glob("*_judged.jsonl")):
            row = ORR_REPORT.summarize_file(path)
            row["orr_float"] = pct_float(row["over_refusal_rate"])
            row["family"] = family(row["model"])
            row["display_model"] = display(row["model"])
            rows[row["model"]] = row
    return sorted(rows.values(), key=lambda row: (row["orr_float"], row["family"], row["model"]))


def category_order(rows: list[dict]) -> list[str]:
    categories = set()
    for row in rows:
        categories.update(str(item) for item in row["by_category"].keys())
    preferred = ["Network attacks", "Ransomware", "Spyware", "Trojan horses", "Viruses", "Worms"]
    return [c for c in preferred if c in categories] + sorted(categories - set(preferred))


def category_rate(stats) -> float:
    total = sum(stats.values())
    valid = total - sum(stats[label] for label in ORR_REPORT.NON_VALID_LABELS)
    if valid <= 0:
        return 0.0
    refusal = sum(stats[label] for label in ORR_REPORT.OVER_REFUSAL_LABELS)
    return refusal / valid * 100


def save_overall_orr(rows: list[dict]) -> None:
    labels = [row["display_model"] for row in rows]
    values = [row["orr_float"] for row in rows]
    families = [row["family"] for row in rows]
    palette = {
        "GPT": "#4C78A8",
        "Claude": "#F58518",
        "Gemini": "#54A24B",
        "Qwen": "#B279A2",
        "DeepSeek": "#E45756",
        "Llama": "#72B7B2",
        "GLM": "#EECA3B",
        "Grok": "#9D755D",
        "Other": "#BAB0AC",
    }
    colors = [palette.get(fam, palette["Other"]) for fam in families]

    fig, ax = plt.subplots(figsize=(7.8, 8.6))
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, alpha=0.9)
    ax.set_yticks(y, labels, fontsize=7)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Over-refusal rate (%)")
    ax.set_title("Overall ORR on Code-ORBench")
    ax.grid(axis="x", linestyle="--", linewidth=0.45, alpha=0.4)
    for idx, value in enumerate(values):
        ax.text(min(value + 1.0, 97.0), idx, f"{value:.1f}", va="center", fontsize=6.5)

    handles = []
    for fam in sorted(set(families)):
        handles.append(plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=palette.get(fam), markersize=7, label=fam))
    ax.legend(handles=handles, ncol=4, loc="lower right", frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "overall_orr.pdf")
    fig.savefig(FIG_DIR / "overall_orr.png", dpi=260)
    plt.close(fig)


def save_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(8.2, 2.65))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    boxes = [
        (0.25, 2.45, 1.55, 0.95, "RMCBench\ncode seeds", "#E7F0FA"),
        (2.15, 2.45, 1.85, 0.95, "Controlled-risk\nrewrite", "#DBECF8"),
        (4.35, 2.45, 1.85, 0.95, "03A safety\nverification", "#E8F3EA"),
        (6.55, 2.45, 1.95, 0.95, "03B refusal\ncalibration", "#FFF4D6"),
        (8.85, 2.45, 1.6, 0.95, "03C fixed\nsplit", "#F4E4F2"),
        (10.75, 2.45, 1.0, 0.95, "392\nprompts", "#F2DCE0"),
    ]
    for x, y, w, h, text, color in boxes:
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=0.9,
            edgecolor="#455A64",
            facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)

    for start, end in [
        ((1.8, 2.925), (2.15, 2.925)),
        ((4.0, 2.925), (4.35, 2.925)),
        ((6.2, 2.925), (6.55, 2.925)),
        ((8.5, 2.925), (8.85, 2.925)),
        ((10.45, 2.925), (10.75, 2.925)),
    ]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, linewidth=0.9, color="#455A64"))

    ax.text(3.05, 1.85, "gpt-5.4 + qwen3-30b", ha="center", fontsize=7.4, color="#4C5B66")
    ax.text(5.28, 1.85, "3-of-4 verifier pass", ha="center", fontsize=7.4, color="#4C5B66")
    ax.text(7.53, 1.85, "mixed refusal behavior", ha="center", fontsize=7.4, color="#4C5B66")

    toxic_box = FancyBboxPatch(
        (0.25, 0.45), 2.25, 0.72,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        linewidth=0.85,
        edgecolor="#455A64",
        facecolor="#F7E3D8",
    )
    ax.add_patch(toxic_box)
    ax.text(1.375, 0.81, "117 aligned toxic-control seeds", ha="center", va="center", fontsize=8.2)
    ax.add_patch(FancyArrowPatch((0.95, 2.45), (1.15, 1.17), arrowstyle="-|>", mutation_scale=10, linewidth=0.85, color="#455A64"))
    ax.text(6.1, 0.62, "Phases 01--03C create the benchmark; Phases 04--06 only evaluate target models.", ha="center", fontsize=8.2)

    fig.tight_layout(pad=0.2)
    fig.savefig(FIG_DIR / "pipeline.pdf")
    fig.savefig(FIG_DIR / "pipeline.png", dpi=260)
    plt.close(fig)


def save_category_heatmap(rows: list[dict]) -> None:
    categories = category_order(rows)
    data = np.array([
        [category_rate(row["by_category"].get(category, {})) for category in categories]
        for row in rows
    ])
    labels = [row["display_model"] for row in rows]
    short_categories = {
        "Network attacks": "Network",
        "Ransomware": "Ransom.",
        "Spyware": "Spyware",
        "Trojan horses": "Trojan",
        "Viruses": "Viruses",
        "Worms": "Worms",
    }

    fig, ax = plt.subplots(figsize=(7.8, 8.8))
    im = ax.imshow(data, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(categories)), [short_categories.get(c, c) for c in categories], rotation=35, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(labels)), labels, fontsize=6.5)
    ax.set_title("Category-level ORR (%)")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=5.3, color="white" if value > 65 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("ORR (%)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "category_heatmap.pdf")
    fig.savefig(FIG_DIR / "category_heatmap.png", dpi=260)
    plt.close(fig)


def save_family_category_heatmap(rows: list[dict]) -> None:
    categories = category_order(rows)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(row)
    fams = sorted(grouped)
    data = []
    for fam in fams:
        fam_rows = grouped[fam]
        data.append([
            sum(category_rate(row["by_category"].get(category, {})) for row in fam_rows) / len(fam_rows)
            for category in categories
        ])
    data = np.array(data)

    fig, ax = plt.subplots(figsize=(7.4, 3.3))
    im = ax.imshow(data, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(categories)), [c.replace(" attacks", "").replace(" horses", "") for c in categories], rotation=30, ha="right")
    ax.set_yticks(np.arange(len(fams)), fams)
    ax.set_title("Family-average ORR by category (%)")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=7, color="white" if value > 65 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("ORR (%)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "family_category_heatmap.pdf")
    fig.savefig(FIG_DIR / "family_category_heatmap.png", dpi=260)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_orr_rows()
    if not rows:
        print("No ORR rows found.", file=sys.stderr)
        raise SystemExit(1)
    save_pipeline()
    save_overall_orr(rows)
    save_category_heatmap(rows)
    save_family_category_heatmap(rows)
    print(f"Wrote {len(rows)}-model ACL figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
