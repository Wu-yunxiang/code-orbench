#!/usr/bin/env python3
"""Prompt diversity analysis for the fixed Code-ORBench split."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*|\d+(?:\.\d+)?|[^\sA-Za-z0-9_]")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def distinct_n(tokenized: list[list[str]], n: int) -> tuple[int, int, float]:
    total = 0
    unique = set()
    for tokens in tokenized:
        grams = ngrams(tokens, n)
        total += len(grams)
        unique.update(grams)
    return len(unique), total, (len(unique) / total if total else 0.0)


def modified_precision(candidate: list[str], reference: list[str], n: int) -> float:
    cand_counts = Counter(ngrams(candidate, n))
    ref_counts = Counter(ngrams(reference, n))
    if not cand_counts:
        return 0.0
    clipped = sum(min(count, ref_counts[gram]) for gram, count in cand_counts.items())
    return clipped / sum(cand_counts.values())


def sentence_bleu(candidate: list[str], reference: list[str], max_order: int = 4) -> float:
    if not candidate or not reference:
        return 0.0
    precisions = []
    for n in range(1, max_order + 1):
        precision = modified_precision(candidate, reference, n)
        # Add-one smoothing keeps short code prompts from collapsing to zero.
        cand_total = max(len(ngrams(candidate, n)), 0)
        precision = (precision * cand_total + 1.0) / (cand_total + 1.0) if cand_total else 1.0
        precisions.append(precision)
    ref_len = len(reference)
    cand_len = len(candidate)
    bp = 1.0 if cand_len > ref_len else math.exp(1 - ref_len / max(cand_len, 1))
    return bp * math.exp(sum(math.log(max(p, 1e-12)) for p in precisions) / max_order)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def flatten_strings(rows: list[dict], key: str) -> set[str]:
    values = set()
    for row in rows:
        value = row.get(key)
        if isinstance(value, list):
            values.update(str(item) for item in value)
        elif value:
            values.add(str(value))
    return values


def analyze(rows: list[dict], near_duplicate_jaccard: float) -> tuple[dict, list[dict], list[dict]]:
    prompts = [row.get("rewritten_prompt", "") for row in rows]
    tokenized = [tokenize(text) for text in prompts]
    token_sets = [set(tokens) for tokens in tokenized]

    summary: dict[str, object] = {
        "total_prompts": len(rows),
        "unique_prompts": len(set(prompts)),
        "exact_duplicate_prompts": len(rows) - len(set(prompts)),
        "unique_source_pids": len({row.get("source_pid") for row in rows}),
        "unique_source_categories": len({row.get("source_category") for row in rows}),
        "unique_prompt_families": len({row.get("prompt_family") for row in rows}),
        "unique_surface_risk_terms": len(flatten_strings(rows, "surface_risk_terms")),
        "unique_surface_risk_term_sets": len({tuple(row.get("surface_risk_terms") or []) for row in rows}),
        "unique_benign_mechanisms": len({row.get("benign_mechanism") for row in rows}),
        "unique_safety_constraint_patterns": len({tuple(row.get("safety_constraints") or []) for row in rows}),
        "unique_forbidden_effect_patterns": len({tuple(row.get("forbidden_real_world_effects") or []) for row in rows}),
        "avg_prompt_tokens": sum(len(tokens) for tokens in tokenized) / len(tokenized),
    }

    distinct_rows = []
    for n in range(1, 5):
        unique, total, ratio = distinct_n(tokenized, n)
        distinct_rows.append({"metric": f"distinct_{n}", "unique": unique, "total": total, "ratio": ratio})
        summary[f"distinct_{n}_ratio"] = ratio
        summary[f"distinct_{n}_unique"] = unique
        summary[f"distinct_{n}_total"] = total

    pair_bleu = []
    pair_jaccard = []
    near_duplicate_pairs = []
    for i, j in combinations(range(len(rows)), 2):
        bleu_ij = sentence_bleu(tokenized[i], tokenized[j])
        bleu_ji = sentence_bleu(tokenized[j], tokenized[i])
        pair_bleu.append((bleu_ij + bleu_ji) / 2)
        jac = jaccard(token_sets[i], token_sets[j])
        pair_jaccard.append(jac)
        if jac >= near_duplicate_jaccard:
            near_duplicate_pairs.append((i, j, jac))

    summary.update(
        {
            "pairwise_self_bleu_mean": sum(pair_bleu) / len(pair_bleu),
            "pairwise_self_bleu_median": percentile(pair_bleu, 0.5),
            "pairwise_self_bleu_p95": percentile(pair_bleu, 0.95),
            "pairwise_self_bleu_max": max(pair_bleu) if pair_bleu else 0.0,
            "pairwise_jaccard_mean": sum(pair_jaccard) / len(pair_jaccard),
            "pairwise_jaccard_p95": percentile(pair_jaccard, 0.95),
            "pairwise_jaccard_max": max(pair_jaccard) if pair_jaccard else 0.0,
            "near_duplicate_jaccard_threshold": near_duplicate_jaccard,
            "near_duplicate_pairs": len(near_duplicate_pairs),
            "near_duplicate_pair_rate": len(near_duplicate_pairs) / len(pair_jaccard) if pair_jaccard else 0.0,
        }
    )

    category_family = Counter((row.get("source_category"), row.get("prompt_family")) for row in rows)
    coverage_rows = [
        {"source_category": category, "prompt_family": family, "count": count}
        for (category, family), count in sorted(category_family.items())
    ]
    return summary, distinct_rows, coverage_rows


def write_summary_csv(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key in sorted(summary):
            value = summary[key]
            if isinstance(value, float):
                writer.writerow([key, f"{value:.6f}"])
            else:
                writer.writerow([key, value])


def write_report(path: Path, summary: dict, distinct_rows: list[dict], coverage_rows: list[dict]) -> None:
    lines = [
        "# Code-ORBench Prompt Diversity Analysis",
        "",
        "- 该分析使用项目内置 tokenizer、pairwise self-BLEU 和 lexical diversity 指标，不依赖 sacreBLEU、BERTScore、torch 或 transformers。",
        f"- 总 prompt 数：{summary['total_prompts']}",
        f"- 唯一 prompt 数：{summary['unique_prompts']}",
        f"- exact duplicate prompts：{summary['exact_duplicate_prompts']}",
        f"- unique surface risk term sets：{summary['unique_surface_risk_term_sets']}",
        f"- unique benign mechanisms：{summary['unique_benign_mechanisms']}",
        f"- unique safety constraint patterns：{summary['unique_safety_constraint_patterns']}",
        f"- pairwise self-BLEU mean：{summary['pairwise_self_bleu_mean']:.3f}",
        f"- pairwise self-BLEU p95：{summary['pairwise_self_bleu_p95']:.3f}",
        f"- near-duplicate pair rate：{summary['near_duplicate_pair_rate'] * 100:.3f}% (Jaccard >= {summary['near_duplicate_jaccard_threshold']})",
        "",
        "## Distinct n-grams",
        "",
        "| metric | unique | total | ratio |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in distinct_rows:
        lines.append(f"| {row['metric']} | {row['unique']} | {row['total']} | {row['ratio']:.3f} |")

    lines.extend(
        [
            "",
            "## Source Category x Prompt Family Coverage",
            "",
            "| source_category | prompt_family | count |",
            "| --- | --- | ---: |",
        ]
    )
    for row in coverage_rows:
        lines.append(f"| {row['source_category']} | {row['prompt_family']} | {row['count']} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_figure(path: Path, distinct_rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = [row["metric"].replace("_", "-") for row in distinct_rows]
    values = [row["ratio"] for row in distinct_rows]
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    ax.bar(labels, values, color="#4C78A8", alpha=0.9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Unique n-gram ratio")
    ax.set_title("Lexical diversity of Code-ORBench prompts")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.025, f"{value:.2f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"), dpi=260)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dataset/full_all/03c_selected_records.jsonl")
    parser.add_argument("--summary-csv", default="dataset/validation/prompt_diversity_summary.csv")
    parser.add_argument("--report-md", default="dataset/validation/prompt_diversity_report.md")
    parser.add_argument("--figure", default="paper/acl/latex/figures/prompt_diversity.pdf")
    parser.add_argument("--near-duplicate-jaccard", type=float, default=0.85)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    summary, distinct_rows, coverage_rows = analyze(rows, args.near_duplicate_jaccard)
    write_summary_csv(Path(args.summary_csv), summary)
    write_report(Path(args.report_md), summary, distinct_rows, coverage_rows)
    write_figure(Path(args.figure), distinct_rows)
    print(
        "wrote diversity analysis: "
        f"prompts={summary['total_prompts']} self_bleu_mean={summary['pairwise_self_bleu_mean']:.3f} "
        f"distinct4={summary['distinct_4_ratio']:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
