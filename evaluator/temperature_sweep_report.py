#!/usr/bin/env python3
"""Aggregate and visualize the temperature sweep experiment."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


FAMILY_BY_MODEL = {
    "claude-sonnet-4-6": "Claude",
    "deepseek-v3.2-thinking": "DeepSeek",
    "glm-4-32b-0414": "GLM",
    "gpt-4o-mini": "GPT",
    "gemini-3-flash-preview-thinking": "Gemini",
    "grok-4": "Grok",
    "llama3.1-8b": "Llama",
    "qwen3.5-397b-a17b": "Qwen",
}


DISPLAY_BY_MODEL = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "deepseek-v3.2-thinking": "DeepSeek V3.2 Thinking",
    "glm-4-32b-0414": "GLM-4-32B",
    "gpt-4o-mini": "GPT-4o mini",
    "gemini-3-flash-preview-thinking": "Gemini 3 Flash Thinking",
    "grok-4": "Grok 4",
    "llama3.1-8b": "Llama 3.1 8B",
    "qwen3.5-397b-a17b": "Qwen3.5 397B-A17B",
}


def parse_temperatures(value: str) -> list[float]:
    return [float(part.strip()) for part in value.replace(" ", ",").split(",") if part.strip()]


def temp_slug(value: float) -> str:
    return f"t{value:.1f}".replace(".", "_")


def read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def label_of(row: dict) -> str:
    return row.get("judge_label") or row.get("label") or row.get("decision") or "UNKNOWN"


def category_of(row: dict) -> str:
    source = row.get("source_record") if isinstance(row.get("source_record"), dict) else {}
    return (
        row.get("source_category")
        or row.get("malicious_category")
        or row.get("category")
        or source.get("source_category")
        or source.get("malicious_category")
        or source.get("category")
        or "Unknown"
    )


def prompt_family_of(row: dict) -> str:
    source = row.get("source_record") if isinstance(row.get("source_record"), dict) else {}
    return row.get("prompt_family") or source.get("prompt_family") or "Unknown"


def summarize_judged_file(path: Path) -> dict:
    counts = Counter()
    by_category: dict[str, Counter] = defaultdict(Counter)
    by_family: dict[str, Counter] = defaultdict(Counter)
    for row in read_jsonl(path) or []:
        label = label_of(row)
        counts[label] += 1
        by_category[category_of(row)][label] += 1
        by_family[prompt_family_of(row)][label] += 1
    refusal = counts["REFUSAL"]
    non_refusal = counts["NON_REFUSAL"]
    valid = refusal + non_refusal
    rate = refusal / valid * 100 if valid else 0.0
    return {
        "valid": valid,
        "refusal": refusal,
        "non_refusal": non_refusal,
        "invalid": sum(value for key, value in counts.items() if key not in {"REFUSAL", "NON_REFUSAL"}),
        "rate": rate,
        "by_category": by_category,
        "by_family": by_family,
    }


def collect(root: Path, temperatures: list[float], models: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    summary_rows = []
    category_rows = []
    family_rows = []
    for temperature in temperatures:
        slug = temp_slug(temperature)
        for model in models:
            orr_path = root / slug / "orr" / "05_judged_refusal_intent" / f"{model}_judged.jsonl"
            toxic_path = root / slug / "toxic" / "05_judged_refusal_intent" / f"{model}_judged.jsonl"
            orr = summarize_judged_file(orr_path)
            toxic = summarize_judged_file(toxic_path)
            family = FAMILY_BY_MODEL.get(model, "Unknown")
            row = {
                "temperature": f"{temperature:.1f}",
                "model": model,
                "display_model": DISPLAY_BY_MODEL.get(model, model),
                "family": family,
                "orr": f"{orr['rate']:.2f}",
                "trr": f"{toxic['rate']:.2f}",
                "trr_minus_orr": f"{toxic['rate'] - orr['rate']:.2f}",
                "orr_valid": orr["valid"],
                "toxic_valid": toxic["valid"],
                "orr_refusal": orr["refusal"],
                "orr_non_refusal": orr["non_refusal"],
                "toxic_refusal": toxic["refusal"],
                "toxic_non_refusal": toxic["non_refusal"],
                "orr_invalid": orr["invalid"],
                "toxic_invalid": toxic["invalid"],
            }
            summary_rows.append(row)
            for category in sorted(set(orr["by_category"]) | set(toxic["by_category"])):
                oc = orr["by_category"].get(category, Counter())
                tc = toxic["by_category"].get(category, Counter())
                ov = oc["REFUSAL"] + oc["NON_REFUSAL"]
                tv = tc["REFUSAL"] + tc["NON_REFUSAL"]
                category_rows.append(
                    {
                        "temperature": f"{temperature:.1f}",
                        "model": model,
                        "family": family,
                        "category": category,
                        "orr_valid": ov,
                        "orr": f"{(oc['REFUSAL'] / ov * 100) if ov else 0.0:.2f}",
                        "orr_refusal": oc["REFUSAL"],
                        "toxic_valid": tv,
                        "trr": f"{(tc['REFUSAL'] / tv * 100) if tv else 0.0:.2f}",
                        "toxic_refusal": tc["REFUSAL"],
                    }
                )
            for prompt_family in sorted(orr["by_family"]):
                fc = orr["by_family"][prompt_family]
                valid = fc["REFUSAL"] + fc["NON_REFUSAL"]
                family_rows.append(
                    {
                        "temperature": f"{temperature:.1f}",
                        "model": model,
                        "family": family,
                        "prompt_family": prompt_family,
                        "valid": valid,
                        "orr": f"{(fc['REFUSAL'] / valid * 100) if valid else 0.0:.2f}",
                        "refusal": fc["REFUSAL"],
                    }
                )
    return summary_rows, category_rows, family_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def slope(rows: list[dict], metric: str, model: str) -> float:
    model_rows = sorted((row for row in rows if row["model"] == model), key=lambda row: float(row["temperature"]))
    if len(model_rows) < 2:
        return 0.0
    return float(model_rows[-1][metric]) - float(model_rows[0][metric])


def make_markdown(path: Path, rows: list[dict], temperatures: list[float], models: list[str]) -> None:
    by_model_temp = {(row["model"], row["temperature"]): row for row in rows}
    lines = [
        "# 温度对 ORR/TRR 的影响",
        "",
        "本实验用于分析采样温度对拒绝行为的影响，不作为 benchmark 主质量评估。ORR 使用 Code-ORBench 100 条分层同源子集；TRR 使用从该子集对应 source seeds 中再分层抽取的 50 条 toxic prompts。05 判断采用新版拒绝意图标准。",
        "",
        "## 代表模型",
        "",
        "| 模型族 | 代表模型 | 选择原因 |",
        "| --- | --- | --- |",
    ]
    for model in models:
        lines.append(
            f"| {FAMILY_BY_MODEL.get(model, 'Unknown')} | `{model}` | 该模型族在全量新版 05 结果中 ORR 最高，用于压力测试温度敏感性 |"
        )

    lines.extend(["", "## 总体结果", ""])
    header = "| 模型 | 指标 | " + " | ".join(f"T={t:.1f}" for t in temperatures) + " | 变化(1.0-0.0) |"
    sep = "| --- | --- | " + " | ".join("---:" for _ in temperatures) + " | ---: |"
    lines.extend([header, sep])
    for model in models:
        for metric, label in [("orr", "ORR"), ("trr", "TRR"), ("trr_minus_orr", "TRR-ORR")]:
            values = []
            for temperature in temperatures:
                row = by_model_temp.get((model, f"{temperature:.1f}"))
                values.append(f"{float(row[metric]):.2f}%" if row else "NA")
            delta = slope(rows, metric, model)
            lines.append(f"| `{model}` | {label} | " + " | ".join(values) + f" | {delta:+.2f} |")

    lines.extend(["", "## 温度敏感性排序", ""])
    lines.append("| 模型 | ORR 变化 | TRR 变化 | 说明 |")
    lines.append("| --- | ---: | ---: | --- |")
    for model in sorted(models, key=lambda item: abs(slope(rows, "orr", item)), reverse=True):
        orr_delta = slope(rows, "orr", model)
        trr_delta = slope(rows, "trr", model)
        note = "ORR 对温度更敏感" if abs(orr_delta) >= abs(trr_delta) else "TRR 对温度更敏感"
        lines.append(f"| `{model}` | {orr_delta:+.2f} | {trr_delta:+.2f} | {note} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figures(fig_dir: Path, rows: list[dict], temperatures: list[float], models: list[str]) -> None:
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)
    for model in by_model:
        by_model[model].sort(key=lambda row: float(row["temperature"]))

    plt.figure(figsize=(10.5, 6.2))
    for model in models:
        model_rows = by_model[model]
        xs = [float(row["temperature"]) for row in model_rows]
        ys = [float(row["orr"]) for row in model_rows]
        plt.plot(xs, ys, marker="o", linewidth=1.8, label=FAMILY_BY_MODEL.get(model, model))
    plt.xlabel("Temperature")
    plt.ylabel("ORR (%)")
    plt.title("Temperature Sensitivity of Over-Refusal")
    plt.grid(alpha=0.25)
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_dir / "temperature_orr_lines.png", dpi=220)
    plt.savefig(fig_dir / "temperature_orr_lines.pdf")
    plt.close()

    plt.figure(figsize=(10.5, 6.2))
    for model in models:
        model_rows = by_model[model]
        xs = [float(row["temperature"]) for row in model_rows]
        ys = [float(row["trr"]) for row in model_rows]
        plt.plot(xs, ys, marker="o", linewidth=1.8, label=FAMILY_BY_MODEL.get(model, model))
    plt.xlabel("Temperature")
    plt.ylabel("TRR (%)")
    plt.title("Temperature Sensitivity of Toxic Prompt Refusal")
    plt.grid(alpha=0.25)
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_dir / "temperature_trr_lines.png", dpi=220)
    plt.savefig(fig_dir / "temperature_trr_lines.pdf")
    plt.close()

    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.2), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, temperature in zip(axes, temperatures):
        temp_rows = [row for row in rows if row["temperature"] == f"{temperature:.1f}"]
        for row in temp_rows:
            ax.scatter(float(row["trr"]), float(row["orr"]), s=42)
            ax.text(float(row["trr"]) + 0.6, float(row["orr"]) + 0.6, row["family"], fontsize=7)
        ax.plot([0, 100], [0, 100], linestyle="--", linewidth=1, color="gray", alpha=0.5)
        ax.set_title(f"T={temperature:.1f}")
        ax.grid(alpha=0.2)
    for ax in axes[3:]:
        ax.set_xlabel("TRR (%)")
    for ax in axes[::3]:
        ax.set_ylabel("ORR (%)")
    fig.suptitle("ORR vs. TRR Across Sampling Temperatures", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "temperature_orr_trr_scatter_grid.png", dpi=220, bbox_inches="tight")
    fig.savefig(fig_dir / "temperature_orr_trr_scatter_grid.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dataset/temperature_sweep")
    parser.add_argument("--temperatures", default="0,0.2,0.4,0.6,0.8,1.0")
    parser.add_argument("--models", nargs="+", default=list(FAMILY_BY_MODEL))
    parser.add_argument("--summary-csv", default="dataset/temperature_sweep/temperature_sweep_summary.csv")
    parser.add_argument("--category-csv", default="dataset/temperature_sweep/temperature_sweep_by_category.csv")
    parser.add_argument("--prompt-family-csv", default="dataset/temperature_sweep/temperature_sweep_by_prompt_family.csv")
    parser.add_argument("--report-md", default="dataset/temperature_sweep/temperature_sweep_report.md")
    parser.add_argument("--figure-dir", default="paper/acl/latex/figures_temperature_sweep")
    args = parser.parse_args()

    temperatures = parse_temperatures(args.temperatures)
    models = [part for item in args.models for part in item.split(",") if part]
    rows, category_rows, family_rows = collect(Path(args.root), temperatures, models)
    write_csv(Path(args.summary_csv), rows)
    write_csv(Path(args.category_csv), category_rows)
    write_csv(Path(args.prompt_family_csv), family_rows)
    make_markdown(Path(args.report_md), rows, temperatures, models)
    make_figures(Path(args.figure_dir), rows, temperatures, models)
    print(f"Wrote {args.summary_csv}")
    print(f"Wrote {args.category_csv}")
    print(f"Wrote {args.prompt_family_csv}")
    print(f"Wrote {args.report_md}")
    print(f"Wrote figures to {args.figure_dir}")


if __name__ == "__main__":
    main()
