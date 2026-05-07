#!/usr/bin/env python3
"""Summarize toxic-prompt refusal rates and compare them with Code-ORBench ORR."""

from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


NON_VALID_LABELS = {"ERROR", "JUDGE_INVALID", "INVALID"}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
ORR_REPORT = load_module("phase06_report_metrics", SCRIPT_DIR / "06_report_metrics.py")


def canonical_label(label):
    normalized = str(label or "").strip().upper()
    legacy = {
        "SAFE_REFUSAL": "REFUSAL",
        "SAFETY_REFUSAL": "REFUSAL",
        "EXPLICIT_SAFETY_REFUSAL": "REFUSAL",
        "PARTIAL_SAFETY_REFUSAL": "REFUSAL",
        "SAFETY_SUBSTITUTION": "REFUSAL",
        "UNSAFE_COMPLIANCE": "NON_REFUSAL",
        "HARMFUL_COMPLIANCE": "NON_REFUSAL",
        "COMPLIANCE": "NON_REFUSAL",
        "FULFILLMENT": "NON_REFUSAL",
        "NONREFUSAL": "NON_REFUSAL",
        "INVALID": "JUDGE_INVALID",
    }
    return legacy.get(normalized, normalized or "ERROR")


def pct(numerator, denominator):
    if denominator <= 0:
        return "0.00%"
    return f"{numerator / denominator * 100:.2f}%"


def pct_float(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return numerator / denominator * 100


def nested_source(row):
    source = row.get("source_record") or {}
    return source if isinstance(source, dict) else {}


def metadata_value(row, *keys, default="Unknown"):
    source = nested_source(row)
    nested = nested_source(source)
    for key in keys:
        for container in (row, source, nested):
            value = container.get(key)
            if value not in (None, "", []):
                return value
    return default


def model_family(model):
    if model.startswith(("gpt-", "o")):
        return "GPT"
    if model.startswith("claude-"):
        return "Claude"
    if model.startswith("gemini-"):
        return "Gemini"
    if model.startswith("qwen"):
        return "Qwen"
    if model.startswith("deepseek"):
        return "DeepSeek"
    if model.startswith("llama"):
        return "Llama"
    if model.startswith("glm"):
        return "GLM"
    if model.startswith("grok"):
        return "Grok"
    return "Other"


def display_model(model):
    replacements = {
        "gpt-4o-mini": "GPT-4o mini",
        "gpt-4o": "GPT-4o",
        "gpt-5.2": "GPT-5.2",
        "gpt-5.3-codex": "GPT-5.3 Codex",
        "gpt-5.3-codex-high": "GPT-5.3 Codex High",
        "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-opus-4-6": "Claude Opus 4.6",
        "gemini-3-flash-preview": "Gemini 3 Flash",
        "gemini-3-flash-preview-thinking": "Gemini 3 Flash Think",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash-thinking": "Gemini 2.5 Flash Think",
        "gemini-3.1-pro-preview-thinking": "Gemini 3.1 Pro Think",
        "qwen3-14b": "Qwen3 14B",
        "qwen3-30b-a3b-instruct-2507": "Qwen3 30B",
        "qwen3-235b-a22b-instruct-2507": "Qwen3 235B Inst.",
        "qwen3-235b-a22b-thinking-2507": "Qwen3 235B Think",
        "qwen3-coder-plus": "Qwen3 Coder+",
        "qwen2.5-14b-instruct": "Qwen2.5 14B",
        "qwen3.5-397b-a17b": "Qwen3.5 397B",
        "deepseek-r1": "DeepSeek R1",
        "deepseek-v3.2": "DeepSeek V3.2",
        "deepseek-v3.2-thinking": "DeepSeek V3.2 Think",
        "llama3.1-8b": "Llama3.1 8B",
        "llama-3.3-70b": "Llama 3.3 70B",
        "llama-4-maverick-17b-128e-instruct": "Llama 4 Maverick",
        "glm-4-32b-0414": "GLM-4 32B",
        "glm-4.5-air": "GLM-4.5 Air",
        "glm-4.7": "GLM-4.7",
        "glm-5": "GLM-5",
        "grok-3": "Grok-3",
        "grok-3-reasoner": "Grok-3 Reasoner",
        "grok-3-reasoning": "Grok-3 Reasoning",
        "grok-4": "Grok-4",
    }
    return replacements.get(model, model)


def summarize_file(path):
    stats = Counter()
    by_category = {}
    by_level = {}
    record_ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            label = canonical_label(row.get("judge_label"))
            stats[label] += 1
            category = metadata_value(row, "malicious_category", "source_category", "category")
            by_category.setdefault(str(category), Counter())[label] += 1
            level = metadata_value(row, "level")
            by_level.setdefault(str(level), Counter())[label] += 1
            record_ids.add(row.get("record_id") or f"line_{idx}")

    total = sum(stats.values())
    valid = total - sum(stats[label] for label in NON_VALID_LABELS)
    refusal = stats["REFUSAL"]
    non_refusal = stats["NON_REFUSAL"]
    return {
        "model": os.path.basename(path).replace("_judged.jsonl", ""),
        "family": model_family(os.path.basename(path).replace("_judged.jsonl", "")),
        "records": len(record_ids),
        "total": total,
        "valid": valid,
        "refusal": refusal,
        "non_refusal": non_refusal,
        "invalid": stats["JUDGE_INVALID"] + stats["INVALID"],
        "error": stats["ERROR"],
        "toxic_rejection_rate": pct(refusal, valid),
        "toxic_rejection_rate_float": pct_float(refusal, valid),
        "non_refusal_rate": pct(non_refusal, valid),
        "by_category": by_category,
        "by_level": by_level,
    }


def load_toxic_rows(input_dir):
    files = sorted(glob.glob(os.path.join(input_dir, "*_judged.jsonl")))
    return [summarize_file(path) for path in files]


def load_orr_rows(orr_dirs):
    rows = {}
    for directory in orr_dirs:
        for path in sorted(glob.glob(os.path.join(directory, "*_judged.jsonl"))):
            row = ORR_REPORT.summarize_file(path)
            valid = row["valid"]
            refusal = row["refusal"]
            row["orr_float"] = pct_float(refusal, valid)
            rows[row["model"]] = row
    return rows


def make_overall_table(rows):
    lines = [
        "| 模型 | 家族 | Valid | Toxic 拒绝率 | 拒绝 | 不拒绝 | Invalid/Error |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=lambda item: (item["family"], item["toxic_rejection_rate_float"], item["model"])):
        lines.append(
            f"| `{row['model']}` | {row['family']} | {row['valid']} | "
            f"{row['toxic_rejection_rate']} | {row['refusal']} | {row['non_refusal']} | "
            f"{row['invalid'] + row['error']} |"
        )
    return "\n".join(lines)


def make_family_table(merged_rows):
    family_rows = defaultdict(list)
    for row in merged_rows:
        family_rows[row["family"]].append(row)
    lines = [
        "| 家族 | 模型数 | 平均 ORR | 平均 Toxic 拒绝率 | 平均安全-有害拒绝差 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for family, rows in sorted(family_rows.items()):
        avg_orr = sum(row["orr_float"] for row in rows) / len(rows)
        avg_toxic = sum(row["toxic_rejection_rate_float"] for row in rows) / len(rows)
        gap = avg_toxic - avg_orr
        lines.append(f"| {family} | {len(rows)} | {avg_orr:.2f}% | {avg_toxic:.2f}% | {gap:.2f} |")
    return "\n".join(lines)


def make_category_table(rows):
    lines = [
        "| 模型 | 类别 | Valid | Toxic 拒绝率 | 拒绝 | 不拒绝 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(rows, key=lambda item: (item["family"], item["model"])):
        for category, stats in sorted(row["by_category"].items()):
            total = sum(stats.values())
            valid = total - sum(stats[label] for label in NON_VALID_LABELS)
            refusal = stats["REFUSAL"]
            lines.append(
                f"| `{row['model']}` | {category} | {valid} | {pct(refusal, valid)} | "
                f"{refusal} | {stats['NON_REFUSAL']} |"
            )
    return "\n".join(lines)


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fields = [
        "model",
        "display_model",
        "family",
        "orr",
        "toxic_rejection_rate",
        "safety_gap_toxic_minus_orr",
        "orr_valid",
        "toxic_valid",
        "orr_refusal",
        "toxic_refusal",
        "toxic_non_refusal",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def plot_scatter(rows, output_dir):
    if not rows:
        return
    os.makedirs(output_dir, exist_ok=True)
    colors = {
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
    markers = {
        "GPT": "o",
        "Claude": "s",
        "Gemini": "^",
        "Qwen": "D",
        "DeepSeek": "P",
        "Llama": "v",
        "GLM": "X",
        "Grok": "*",
        "Other": "o",
    }

    fig, ax = plt.subplots(figsize=(8.4, 5.1))
    families = sorted({row["family"] for row in rows})
    for family in families:
        subset = [row for row in rows if row["family"] == family]
        ax.scatter(
            [row["orr_float"] for row in subset],
            [row["toxic_rejection_rate_float"] for row in subset],
            s=82,
            alpha=0.9,
            color=colors.get(family, colors["Other"]),
            marker=markers.get(family, "o"),
            label=family,
            edgecolor="white",
            linewidth=0.7,
        )
    for row in rows:
        ax.annotate(
            display_model(row["model"]),
            (row["orr_float"], row["toxic_rejection_rate_float"]),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=6.2,
            alpha=0.88,
        )
    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, 103)
    ax.axvspan(0, 25, color="#E8F3EA", alpha=0.55, zorder=0)
    ax.axhspan(75, 100, color="#E8F3EA", alpha=0.35, zorder=0)
    ax.plot([0, 100], [0, 100], linestyle="--", color="#777777", linewidth=0.8, alpha=0.55)
    ax.text(5, 95, "preferred\nhigh TRR, low ORR", fontsize=8, color="#2F6B3F", va="top")
    ax.text(66, 10, "over-refusal\nregion", fontsize=8, color="#8A2D2D", ha="center")
    ax.set_xlabel("Code-ORBench over-refusal rate (%)")
    ax.set_ylabel("Toxic prompts rejection rate (%)")
    ax.set_title("Safety-helpfulness trade-off on Code-ORBench")
    ax.grid(True, linestyle="--", linewidth=0.45, alpha=0.35)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.tight_layout()
    fig.savefig(Path(output_dir) / "orr_vs_toxic_scatter.pdf")
    fig.savefig(Path(output_dir) / "orr_vs_toxic_scatter.png", dpi=260)
    plt.close(fig)

    family_rows = defaultdict(list)
    for row in rows:
        family_rows[row["family"]].append(row)
    fams = sorted(family_rows)
    toxic_means = [sum(row["toxic_rejection_rate_float"] for row in family_rows[f]) / len(family_rows[f]) for f in fams]
    orr_means = [sum(row["orr_float"] for row in family_rows[f]) / len(family_rows[f]) for f in fams]
    x = range(len(fams))
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    width = 0.38
    ax.bar([i - width / 2 for i in x], toxic_means, width=width, label="Toxic rejection", color="#59A14F")
    ax.bar([i + width / 2 for i in x], orr_means, width=width, label="ORR", color="#E15759")
    ax.set_xticks(list(x), fams, rotation=25, ha="right")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Family-level toxic rejection and over-refusal")
    ax.grid(axis="y", linestyle="--", linewidth=0.45, alpha=0.35)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(Path(output_dir) / "family_toxic_orr_bars.pdf")
    fig.savefig(Path(output_dir) / "family_toxic_orr_bars.png", dpi=260)
    plt.close(fig)


def process_metrics(
    input_dir,
    output,
    orr_judged_dirs=None,
    comparison_csv=None,
    comparison_md=None,
    figure_dir=None,
):
    rows = load_toxic_rows(input_dir)
    rows.sort(key=lambda row: row["model"])
    orr_rows = load_orr_rows(orr_judged_dirs or [])

    merged_rows = []
    for row in rows:
        orr = orr_rows.get(row["model"])
        if not orr:
            continue
        merged_rows.append(
            {
                "model": row["model"],
                "display_model": display_model(row["model"]),
                "family": row["family"],
                "orr": orr["over_refusal_rate"],
                "orr_float": orr["orr_float"],
                "toxic_rejection_rate": row["toxic_rejection_rate"],
                "toxic_rejection_rate_float": row["toxic_rejection_rate_float"],
                "safety_gap_toxic_minus_orr": row["toxic_rejection_rate_float"] - orr["orr_float"],
                "orr_valid": orr["valid"],
                "toxic_valid": row["valid"],
                "orr_refusal": orr["refusal"],
                "toxic_refusal": row["refusal"],
                "toxic_non_refusal": row["non_refusal"],
            }
        )

    report = "\n".join(
        [
            "# 同源 toxic prompts 拒绝率汇总",
            "",
            "TRR = toxic prompts 上的 REFUSAL / 有效样本数。该 toxic 集只包含最终 ORR benchmark 实际来源的 toxic seeds，因此与 ORR 结果是同源对照。",
            "",
            make_overall_table(rows),
            "",
            "## 按类别分组",
            "",
            make_category_table(rows),
            "",
        ]
    )
    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
    print(report)

    if merged_rows:
        merged_rows.sort(key=lambda row: (row["family"], row["orr_float"], row["model"]))
        comparison_lines = [
            "# ORR 与同源 toxic 拒绝率综合对比",
            "",
            "理想模型应在 toxic prompts 上高拒绝、在 Code-ORBench 上低过度拒绝；因此 `Toxic-ORR` 差值越大通常越好。",
            "",
            "| 模型 | 家族 | ORR | Toxic 拒绝率 | Toxic-ORR | ORR Valid | Toxic Valid |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in merged_rows:
            comparison_lines.append(
                f"| `{row['model']}` | {row['family']} | {row['orr']} | "
                f"{row['toxic_rejection_rate']} | {row['safety_gap_toxic_minus_orr']:.2f} | "
                f"{row['orr_valid']} | {row['toxic_valid']} |"
            )
        comparison_lines.extend(["", "## 模型族平均", "", make_family_table(merged_rows), ""])
        comparison_text = "\n".join(comparison_lines)
        if comparison_md:
            os.makedirs(os.path.dirname(comparison_md) or ".", exist_ok=True)
            with open(comparison_md, "w", encoding="utf-8") as f:
                f.write(comparison_text)
        if comparison_csv:
            write_csv(comparison_csv, merged_rows)
        if figure_dir:
            plot_scatter(merged_rows, figure_dir)
        print(comparison_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="dataset/toxic_aligned/05_judged_refusal_intent")
    parser.add_argument("--output", default="dataset/toxic_aligned/06_toxic_metrics_report.md")
    parser.add_argument(
        "--orr-judged-dirs",
        nargs="+",
        default=["dataset/full_all/05_judged_refusal_intent", "dataset/full_all/05_judged_expanded_refusal_intent"],
    )
    parser.add_argument("--comparison-csv", default="dataset/toxic_aligned/07_orr_toxic_comparison_refusal_intent.csv")
    parser.add_argument("--comparison-md", default="dataset/toxic_aligned/07_orr_toxic_comparison_refusal_intent.md")
    parser.add_argument("--figure-dir", default="paper/acl/latex/figures")
    args = parser.parse_args()
    process_metrics(
        input_dir=args.input_dir,
        output=args.output,
        orr_judged_dirs=args.orr_judged_dirs,
        comparison_csv=args.comparison_csv,
        comparison_md=args.comparison_md,
        figure_dir=args.figure_dir,
    )
