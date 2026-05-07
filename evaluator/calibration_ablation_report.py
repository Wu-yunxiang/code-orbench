#!/usr/bin/env python3
"""Summarize the 03B calibration ablation."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def find_judged_file(model: str, dirs: list[Path]) -> Path | None:
    for directory in dirs:
        path = directory / f"{model}_judged.jsonl"
        if path.exists():
            return path
    return None


def rate_counts(row: dict) -> tuple[int, int, int, float]:
    valid = row["valid"]
    refusal = row["refusal"]
    non_refusal = row["non_refusal"]
    rate = pct_float(row["over_refusal_rate"])
    return valid, refusal, non_refusal, rate


def combine_rows(model: str, selected: dict, rejected: dict) -> dict:
    valid = selected["valid"] + rejected["valid"]
    refusal = selected["refusal"] + rejected["refusal"]
    non_refusal = selected["non_refusal"] + rejected["non_refusal"]
    rate = refusal / valid * 100 if valid else 0.0
    return {
        "model": model,
        "valid": valid,
        "refusal": refusal,
        "non_refusal": non_refusal,
        "over_refusal_rate": f"{rate:.2f}%",
    }


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j + 2) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def summarize_rates(values: list[float], near_zero_threshold: float) -> dict:
    mean = sum(values) / len(values) if values else 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values) if values else 0.0
    return {
        "mean": mean,
        "min": min(values) if values else 0.0,
        "max": max(values) if values else 0.0,
        "std": math.sqrt(variance),
        "near_zero_models": sum(1 for value in values if value <= near_zero_threshold),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "model",
        "family",
        "selected_valid",
        "selected_orr",
        "rejected_valid",
        "rejected_orr",
        "combined_valid",
        "combined_orr",
        "selected_minus_rejected",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict], aggregate: dict) -> None:
    lines = [
        "# Calibration Ablation Report",
        "",
        "该报告比较 03C selected split 与 03B rejected split，用于验证 refusal-potential calibration 是否提高边界密度。",
        "",
        "## Aggregate",
        "",
        "| split | prompts | mean ORR | range | std | near-zero models |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["selected", "rejected", "combined"]:
        item = aggregate[split]
        lines.append(
            f"| {split} | {item['prompts']} | {item['mean']:.2f}% | "
            f"{item['min']:.2f}--{item['max']:.2f}% | {item['std']:.2f} | {item['near_zero_models']} |"
        )
    lines.extend(
        [
            "",
            f"- selected/rejected Pearson correlation: {aggregate['selected_rejected_pearson']:.3f}",
            f"- selected/rejected Spearman correlation: {aggregate['selected_rejected_spearman']:.3f}",
            "",
            "## Per Model",
            "",
            "| model | family | selected ORR | rejected ORR | combined ORR | selected - rejected |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['model']}` | {row['family']} | {row['selected_orr']:.2f}% | "
            f"{row['rejected_orr']:.2f}% | {row['combined_orr']:.2f}% | "
            f"{row['selected_minus_rejected']:.2f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--selected-judged-dirs", nargs="+", default=[
        "dataset/full_all/05_judged_refusal_intent",
        "dataset/full_all/05_judged_expanded_refusal_intent",
    ])
    parser.add_argument("--rejected-judged-dir", default="dataset/ablation/calibration/05_judged_rejected_refusal_intent")
    parser.add_argument("--summary-csv", default="dataset/ablation/calibration/calibration_ablation_summary.csv")
    parser.add_argument("--report-md", default="dataset/ablation/calibration/calibration_ablation_report.md")
    parser.add_argument("--near-zero-threshold", type=float, default=5.0)
    args = parser.parse_args()

    selected_dirs = [Path(path) for path in args.selected_judged_dirs]
    rejected_dir = Path(args.rejected_judged_dir)
    rows = []
    selected_rates = []
    rejected_rates = []
    combined_rates = []

    for model in args.models:
        selected_file = find_judged_file(model, selected_dirs)
        rejected_file = rejected_dir / f"{model}_judged.jsonl"
        if selected_file is None:
            raise SystemExit(f"Missing selected judged file for {model}")
        if not rejected_file.exists():
            raise SystemExit(f"Missing rejected judged file for {model}: {rejected_file}")
        selected = ORR_REPORT.summarize_file(selected_file)
        rejected = ORR_REPORT.summarize_file(rejected_file)
        combined = combine_rows(model, selected, rejected)
        selected_valid, _, _, selected_rate = rate_counts(selected)
        rejected_valid, _, _, rejected_rate = rate_counts(rejected)
        combined_valid, _, _, combined_rate = rate_counts(combined)
        rows.append(
            {
                "model": model,
                "family": TOXIC_REPORT.model_family(model),
                "selected_valid": selected_valid,
                "selected_orr": selected_rate,
                "rejected_valid": rejected_valid,
                "rejected_orr": rejected_rate,
                "combined_valid": combined_valid,
                "combined_orr": combined_rate,
                "selected_minus_rejected": selected_rate - rejected_rate,
            }
        )
        selected_rates.append(selected_rate)
        rejected_rates.append(rejected_rate)
        combined_rates.append(combined_rate)

    aggregate = {
        "selected": {"prompts": 392, **summarize_rates(selected_rates, args.near_zero_threshold)},
        "rejected": {"prompts": 206, **summarize_rates(rejected_rates, args.near_zero_threshold)},
        "combined": {"prompts": 598, **summarize_rates(combined_rates, args.near_zero_threshold)},
        "selected_rejected_pearson": pearson(selected_rates, rejected_rates),
        "selected_rejected_spearman": pearson(rank(selected_rates), rank(rejected_rates)),
    }
    rows.sort(key=lambda row: (row["family"], row["model"]))
    write_csv(Path(args.summary_csv), rows)
    write_report(Path(args.report_md), rows, aggregate)
    print(f"wrote calibration ablation report for {len(rows)} models", flush=True)


if __name__ == "__main__":
    main()
