#!/usr/bin/env python3
"""Prepare the aligned toxic-prompt control set for Code-ORBench."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path


def read_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def read_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pid_sort_key(pid: str) -> tuple[int, str]:
    try:
        return (0, f"{int(pid):08d}")
    except (TypeError, ValueError):
        return (1, str(pid))


def selected_source_pids(selected_records_path: str) -> tuple[set[str], Counter]:
    records = read_jsonl(selected_records_path)
    counts = Counter()
    for item in records:
        pid = item.get("source_pid") or item.get("pid")
        if pid is not None:
            counts[str(pid)] += 1
    return set(counts), counts


def filtered_seed_pids(filtered_seeds_path: str) -> tuple[set[str], Counter]:
    seeds = read_json(filtered_seeds_path)
    counts = Counter(str(item.get("pid")) for item in seeds if item.get("pid") is not None)
    return set(counts), counts


def normalize_toxic_seed(item: dict, source_counts: Counter) -> dict:
    pid = str(item.get("pid"))
    category = item.get("malicious categories") or item.get("category") or "Unknown"
    return {
        "record_id": f"toxic-{pid}",
        "pid": item.get("pid"),
        "source_pid": item.get("pid"),
        "category": item.get("category"),
        "task": item.get("task"),
        "level": item.get("level"),
        "level_description": item.get("level description"),
        "malicious_functionality": item.get("malicious functionality"),
        "malicious_category": category,
        "source_category": category,
        "prompt": item.get("prompt", ""),
        "alignment_metadata": {
            "aligned_to": "dataset/full_all/03c_selected_records.jsonl",
            "orr_selected_records_from_this_seed": source_counts.get(pid, 0),
        },
    }


def write_jsonl(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_report(path: str, records: list[dict], source: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    categories = Counter(item.get("malicious_category") or "Unknown" for item in records)
    levels = Counter(str(item.get("level") or "Unknown") for item in records)
    lines = [
        "# 同源 toxic prompts 输入集",
        "",
        f"来源策略：`{source}`",
        f"样本数：{len(records)}",
        "",
        "## 类别分布",
        "",
        "| 类别 | 数量 |",
        "| --- | ---: |",
    ]
    for category, count in categories.most_common():
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Level 分布", "", "| Level | 数量 |", "| --- | ---: |"])
    for level, count in sorted(levels.items()):
        lines.append(f"| {level} | {count} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toxic-seeds", default="toxic_seeds/prompt.json")
    parser.add_argument("--selected-records", default="dataset/full_all/03c_selected_records.jsonl")
    parser.add_argument("--filtered-seeds", default="dataset/full_all/01_filtered_seeds.json")
    parser.add_argument(
        "--seed-source",
        choices=["selected", "filtered"],
        default="selected",
        help="selected uses only source_pid values represented in the final ORR split; filtered uses all 01 seeds.",
    )
    parser.add_argument("--output", default="dataset/toxic_aligned/01_toxic_prompts.jsonl")
    parser.add_argument("--report", default="dataset/toxic_aligned/01_toxic_prompts_report.md")
    args = parser.parse_args()

    if args.seed_source == "selected":
        pids, counts = selected_source_pids(args.selected_records)
    else:
        pids, counts = filtered_seed_pids(args.filtered_seeds)

    toxic_by_pid = {str(item.get("pid")): item for item in read_json(args.toxic_seeds)}
    missing = sorted((pid for pid in pids if pid not in toxic_by_pid), key=pid_sort_key)
    if missing:
        raise SystemExit(f"Missing {len(missing)} pid(s) from toxic seed file: {missing[:20]}")

    records = [
        normalize_toxic_seed(toxic_by_pid[pid], counts)
        for pid in sorted(pids, key=pid_sort_key)
    ]
    write_jsonl(args.output, records)
    write_report(args.report, records, args.seed_source)
    print(f"Wrote {len(records)} aligned toxic prompts to {args.output}")
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
