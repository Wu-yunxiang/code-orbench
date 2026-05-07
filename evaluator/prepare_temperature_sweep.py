#!/usr/bin/env python3
"""Prepare aligned ORR/toxic samples for the temperature sweep experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stable_key(*parts: object) -> str:
    text = "||".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def largest_remainder_quotas(counts: Counter, sample_size: int) -> dict[str, int]:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("cannot allocate quotas from empty counts")
    raw = {key: counts[key] / total * sample_size for key in counts}
    quotas = {key: int(value) for key, value in raw.items()}
    remaining = sample_size - sum(quotas.values())
    ranked = sorted(counts, key=lambda key: (raw[key] - quotas[key], counts[key], key), reverse=True)
    for key in ranked[:remaining]:
        quotas[key] += 1
    return quotas


def category_of(row: dict) -> str:
    return row.get("source_category") or row.get("malicious_category") or row.get("category") or "Unknown"


def choose_source_pids(
    toxic_rows: list[dict],
    available_pids: set[int],
    sample_size: int,
    seed: str,
) -> tuple[list[int], dict[str, int]]:
    toxic_by_pid = {
        int(row.get("source_pid") or row.get("pid")): row
        for row in toxic_rows
        if row.get("source_pid") is not None or row.get("pid") is not None
    }
    eligible_rows = [row for pid, row in toxic_by_pid.items() if pid in available_pids]
    by_category: dict[str, list[int]] = defaultdict(list)
    for row in eligible_rows:
        pid = int(row.get("source_pid") or row.get("pid"))
        by_category[category_of(row)].append(pid)

    category_counts = Counter({category: len(pids) for category, pids in by_category.items()})
    quotas = largest_remainder_quotas(category_counts, sample_size)

    selected: list[int] = []
    for category, quota in sorted(quotas.items()):
        pids = sorted(
            by_category[category],
            key=lambda pid: stable_key(seed, category, pid),
        )
        if quota > len(pids):
            raise ValueError(f"quota for {category} exceeds available source pids")
        selected.extend(pids[:quota])

    selected.sort(key=lambda pid: stable_key(seed, "global", pid))
    return selected, quotas


def choose_toxic_subset_pids(
    toxic_rows: list[dict],
    allowed_pids: set[int],
    sample_size: int,
    seed: str,
) -> tuple[list[int], dict[str, int]]:
    eligible_rows = [
        row for row in toxic_rows
        if int(row.get("source_pid") or row.get("pid")) in allowed_pids
    ]
    by_category: dict[str, list[int]] = defaultdict(list)
    for row in eligible_rows:
        pid = int(row.get("source_pid") or row.get("pid"))
        by_category[category_of(row)].append(pid)

    category_counts = Counter({category: len(pids) for category, pids in by_category.items()})
    quotas = largest_remainder_quotas(category_counts, sample_size)
    selected: list[int] = []
    for category, quota in sorted(quotas.items()):
        pids = sorted(
            by_category[category],
            key=lambda pid: stable_key(seed, "toxic", category, pid),
        )
        if quota > len(pids):
            raise ValueError(f"toxic quota for {category} exceeds available source pids")
        selected.extend(pids[:quota])
    selected.sort(key=lambda pid: stable_key(seed, "toxic-global", pid))
    return selected, quotas


def choose_one_record_per_pid(records: list[dict], selected_pids: list[int], seed: str) -> list[dict]:
    by_pid: dict[int, list[dict]] = defaultdict(list)
    for row in records:
        pid = row.get("source_pid")
        if pid is not None:
            by_pid[int(pid)].append(row)

    slot_counts: Counter[str] = Counter()
    generator_counts: Counter[str] = Counter()
    selected_records: list[dict] = []

    for pid in selected_pids:
        candidates = by_pid.get(pid, [])
        if not candidates:
            raise ValueError(f"source_pid {pid} is not present in ORR records")

        def score(row: dict) -> tuple[int, int, str]:
            slot = str(row.get("template_slot") or "Unknown")
            generator = str(row.get("generator_model") or "Unknown")
            return (
                slot_counts[slot],
                generator_counts[generator],
                stable_key(seed, pid, row.get("record_id")),
            )

        chosen = min(candidates, key=score)
        slot_counts[str(chosen.get("template_slot") or "Unknown")] += 1
        generator_counts[str(chosen.get("generator_model") or "Unknown")] += 1
        selected_records.append(chosen)

    selected_records.sort(key=lambda row: (category_of(row), int(row.get("source_pid")), row.get("record_id", "")))
    return selected_records


def write_report(
    path: Path,
    selected_records: list[dict],
    selected_toxic: list[dict],
    orr_quotas: dict[str, int],
    toxic_quotas: dict[str, int],
    source_counts: Counter,
    full_record_counts: Counter,
    seed: str,
) -> None:
    lines = [
        "# 温度实验抽样说明",
        "",
        f"- 抽样随机种子：`{seed}`",
        f"- ORR 样本数：{len(selected_records)}",
        f"- Toxic 同源样本数：{len(selected_toxic)}",
        "- 抽样原则：从全量 392 条 Code-ORBench 记录中抽出 ORR 子集，并保证每条来自不同 `source_pid`；toxic 子集再从这些 ORR 子集对应的 `source_pid` 中分层抽取。",
        "- 类别配额：按 117 个可用 source seed 的类别分布分层，而不是按 392 条 ORR 记录的重复候选分布分层；这样优先保证 ORR/TRR 的同源可比性。",
        "- 记录选择：每个 `source_pid` 只取一条 ORR 记录，并在可选记录中尽量平衡 `template_slot` 与 `generator_model`。",
        "",
        "## 类别配额",
        "",
        "| 类别 | source seed 总数 | full ORR 记录数 | ORR 配额 | ORR 实际 | Toxic 配额 | Toxic 实际 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    orr_counts = Counter(category_of(row) for row in selected_records)
    toxic_counts = Counter(category_of(row) for row in selected_toxic)
    for category in sorted(source_counts):
        lines.append(
            f"| {category} | {source_counts[category]} | {full_record_counts.get(category, 0)} | "
            f"{orr_quotas.get(category, 0)} | {orr_counts.get(category, 0)} | "
            f"{toxic_quotas.get(category, 0)} | {toxic_counts.get(category, 0)} |"
        )

    lines.extend(
        [
            "",
            "## 结构平衡",
            "",
            "| 字段 | 分布 |",
            "| --- | --- |",
            f"| `template_slot` | `{dict(sorted(Counter(str(row.get('template_slot') or 'Unknown') for row in selected_records).items()))}` |",
            f"| `generator_model` | `{dict(sorted(Counter(str(row.get('generator_model') or 'Unknown') for row in selected_records).items()))}` |",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orr-input", default="dataset/full_all/03c_selected_records.jsonl")
    parser.add_argument("--toxic-input", default="dataset/toxic_aligned/01_toxic_prompts.jsonl")
    parser.add_argument("--orr-output", default="dataset/temperature_sweep/01_orr_sample_100.jsonl")
    parser.add_argument("--toxic-output", default="dataset/temperature_sweep/01_toxic_sample_50.jsonl")
    parser.add_argument("--report-output", default="dataset/temperature_sweep/01_sample_report.md")
    parser.add_argument("--orr-sample-size", type=int, default=100)
    parser.add_argument("--toxic-sample-size", type=int, default=50)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Backward-compatible alias for --orr-sample-size.",
    )
    parser.add_argument("--seed", default="code-orbench-temperature-sweep-v1")
    args = parser.parse_args()
    if args.sample_size is not None:
        args.orr_sample_size = args.sample_size

    records = read_jsonl(Path(args.orr_input))
    toxic_rows = read_jsonl(Path(args.toxic_input))
    available_pids = {int(row["source_pid"]) for row in records if row.get("source_pid") is not None}

    selected_pids, orr_quotas = choose_source_pids(
        toxic_rows=toxic_rows,
        available_pids=available_pids,
        sample_size=args.orr_sample_size,
        seed=args.seed,
    )
    selected_records = choose_one_record_per_pid(records, selected_pids, args.seed)

    selected_pid_set = {int(row["source_pid"]) for row in selected_records}
    if args.toxic_sample_size > len(selected_pid_set):
        raise ValueError("--toxic-sample-size cannot exceed the ORR sample size")
    toxic_pids, toxic_quotas = choose_toxic_subset_pids(
        toxic_rows=toxic_rows,
        allowed_pids=selected_pid_set,
        sample_size=args.toxic_sample_size,
        seed=args.seed,
    )
    toxic_pid_set = set(toxic_pids)
    selected_toxic = [
        row for row in toxic_rows
        if int(row.get("source_pid") or row.get("pid")) in toxic_pid_set
    ]
    selected_toxic.sort(key=lambda row: int(row.get("source_pid") or row.get("pid")))

    if len(selected_records) != args.orr_sample_size:
        raise ValueError(f"expected {args.orr_sample_size} ORR records, got {len(selected_records)}")
    if len(selected_toxic) != args.toxic_sample_size:
        raise ValueError(f"expected {args.toxic_sample_size} toxic records, got {len(selected_toxic)}")

    write_jsonl(Path(args.orr_output), selected_records)
    write_jsonl(Path(args.toxic_output), selected_toxic)
    source_counts = Counter(category_of(row) for row in toxic_rows if int(row.get("source_pid") or row.get("pid")) in available_pids)
    full_record_counts = Counter(category_of(row) for row in records)
    write_report(
        path=Path(args.report_output),
        selected_records=selected_records,
        selected_toxic=selected_toxic,
        orr_quotas=orr_quotas,
        toxic_quotas=toxic_quotas,
        source_counts=source_counts,
        full_record_counts=full_record_counts,
        seed=args.seed,
    )
    print(f"Wrote {args.orr_output}")
    print(f"Wrote {args.toxic_output}")
    print(f"Wrote {args.report_output}")


if __name__ == "__main__":
    main()
