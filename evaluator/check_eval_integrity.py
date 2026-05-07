#!/usr/bin/env python3
"""Check ORR/toxic evaluation completeness without modifying checkpoints."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path


ORR_ORIGINAL_MODELS = [
    "gpt-4o-mini",
    "qwen3-14b",
    "qwen3-30b-a3b-instruct-2507",
    "qwen3-235b-a22b-instruct-2507",
    "qwen3-235b-a22b-thinking-2507",
    "qwen3-coder-plus",
    "gemini-3-flash-preview",
    "claude-haiku-4-5-20251001",
    "gpt-4o",
]

ORR_EXPANDED_MODELS = [
    "gpt-5.2",
    "gpt-5.3-codex",
    "gpt-5.3-codex-high",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "gemini-3-flash-preview-thinking",
    "gemini-2.5-pro",
    "gemini-2.5-flash-thinking",
    "gemini-3.1-pro-preview-thinking",
    "qwen2.5-14b-instruct",
    "qwen3.5-397b-a17b",
    "deepseek-r1",
    "deepseek-v3.2",
    "deepseek-v3.2-thinking",
    "llama3.1-8b",
    "llama-3.3-70b",
    "llama-4-maverick-17b-128e-instruct",
    "glm-4-32b-0414",
    "glm-4.5-air",
    "glm-4.7",
    "glm-5",
    "grok-3",
    "grok-3-reasoner",
    "grok-3-reasoning",
    "grok-4",
]


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
PHASE04 = load_module("phase04_run_inference", str(SCRIPT_DIR / "04_run_inference.py"))
PHASE05 = load_module("phase05_llm_judge", str(SCRIPT_DIR / "05_llm_judge.py"))
TOXIC_JUDGE = load_module("toxic_refusal_judge", str(SCRIPT_DIR / "toxic_refusal_judge.py"))


def expected_ids(input_file: str) -> set[str]:
    return {item["record_id"] for item in PHASE04.load_records(input_file)}


def status(path: str, module, expected: set[str], judge: bool = False) -> dict:
    path_obj = Path(path)
    if not path_obj.exists():
        return {
            "rows": 0,
            "valid": 0,
            "missing": len(expected),
            "bad": 0,
            "error": 0,
            "empty": 0,
            "duplicate": 0,
            "wrong": 0,
            "response_dup_groups": 0,
            "response_dup_rows": 0,
            "labels": Counter(),
            "complete": False,
        }

    seen = set()
    valid = set()
    labels = Counter()
    rows = 0
    bad = 0
    error = 0
    empty = 0
    duplicate = 0
    wrong = 0
    response_counts = Counter()

    with path_obj.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            rows += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            record_id = module.compute_record_id(item, idx)
            if record_id in seen:
                duplicate += 1
                continue
            seen.add(record_id)
            if record_id not in expected:
                wrong += 1
                bad += 1
                continue
            if judge:
                label = module.canonical_label(item.get("judge_label"))
                labels[label] += 1
                if module.is_completed_judge_item(item):
                    valid.add(record_id)
                else:
                    bad += 1
            else:
                response = str(item.get("response") or "").strip()
                if item.get("success") and not response:
                    empty += 1
                if not item.get("success"):
                    error += 1
                if module.is_completed_checkpoint_item(item):
                    valid.add(record_id)
                    # Exact repeated successful outputs can indicate a provider/cache issue.
                    # We keep this diagnostic separate from validity because short generic
                    # refusal messages may legitimately repeat.
                    response_counts[" ".join(response.split())] += 1
                else:
                    bad += 1

    duplicate_response_groups = sum(1 for _, count in response_counts.items() if count > 1)
    duplicate_response_rows = sum(count for _, count in response_counts.items() if count > 1)

    return {
        "rows": rows,
        "valid": len(valid),
        "missing": len(expected - valid),
        "bad": bad,
        "error": error,
        "empty": empty,
        "duplicate": duplicate,
        "wrong": wrong,
        "response_dup_groups": duplicate_response_groups,
        "response_dup_rows": duplicate_response_rows,
        "labels": labels,
        "complete": len(valid) == len(expected),
    }


def rate(labels: Counter, denominator: int) -> str:
    if denominator <= 0:
        return "NA"
    return f"{labels.get('REFUSAL', 0) / denominator * 100:.2f}%"


def print_section(title: str, rows: list[dict]) -> None:
    print(f"\n## {title}")
    print("model\t04_valid\t04_missing\t04_bad\t04_error\t04_empty\t04_dup\t04_wrong\t04_resp_dup_groups\t04_resp_dup_rows\t05_valid\t05_missing\t05_bad\t05_dup\t05_wrong\trate")
    for row in rows:
        print(
            f"{row['model']}\t"
            f"{row['s4']['valid']}\t{row['s4']['missing']}\t{row['s4']['bad']}\t{row['s4']['error']}\t"
            f"{row['s4']['empty']}\t{row['s4']['duplicate']}\t{row['s4']['wrong']}\t"
            f"{row['s4']['response_dup_groups']}\t{row['s4']['response_dup_rows']}\t"
            f"{row['s5']['valid']}\t{row['s5']['missing']}\t{row['s5']['bad']}\t"
            f"{row['s5']['duplicate']}\t{row['s5']['wrong']}\t{row['rate']}"
        )


def print_response_duplicate_section(title: str, rows: list[dict]) -> None:
    duplicate_rows = [
        row for row in rows
        if row["s4"]["response_dup_groups"] or row["s4"]["response_dup_rows"]
    ]
    print(f"\n## {title}")
    if not duplicate_rows:
        print("No exact repeated successful response texts detected.")
        return
    print("model\t04_resp_dup_groups\t04_resp_dup_rows")
    for row in duplicate_rows:
        print(
            f"{row['model']}\t"
            f"{row['s4']['response_dup_groups']}\t"
            f"{row['s4']['response_dup_rows']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orr-input", default="dataset/full_all/03c_selected_records.jsonl")
    parser.add_argument("--toxic-input", default="dataset/toxic_aligned/01_toxic_prompts.jsonl")
    parser.add_argument("--orr-original-inference-dir", default="dataset/full_all/04_inference")
    parser.add_argument("--orr-original-judged-dir", default="dataset/full_all/05_judged")
    parser.add_argument("--orr-expanded-inference-dir", default="dataset/full_all/04_inference_expanded")
    parser.add_argument("--orr-expanded-judged-dir", default="dataset/full_all/05_judged_expanded")
    parser.add_argument("--toxic-inference-dir", default="dataset/toxic_aligned/04_inference")
    parser.add_argument("--toxic-judged-dir", default="dataset/toxic_aligned/05_judged")
    args = parser.parse_args()

    orr_expected = expected_ids(args.orr_input)
    toxic_expected = expected_ids(args.toxic_input)

    orr_rows = []
    for model in ORR_ORIGINAL_MODELS:
        s4 = status(f"{args.orr_original_inference_dir}/{model}.jsonl", PHASE04, orr_expected)
        s5 = status(f"{args.orr_original_judged_dir}/{model}_judged.jsonl", PHASE05, orr_expected, judge=True)
        orr_rows.append({"model": model, "s4": s4, "s5": s5, "rate": rate(s5["labels"], s5["valid"])})
    for model in ORR_EXPANDED_MODELS:
        s4 = status(f"{args.orr_expanded_inference_dir}/{model}.jsonl", PHASE04, orr_expected)
        s5 = status(f"{args.orr_expanded_judged_dir}/{model}_judged.jsonl", PHASE05, orr_expected, judge=True)
        orr_rows.append({"model": model, "s4": s4, "s5": s5, "rate": rate(s5["labels"], s5["valid"])})

    toxic_rows = []
    for model in ORR_ORIGINAL_MODELS + ORR_EXPANDED_MODELS:
        s4 = status(f"{args.toxic_inference_dir}/{model}.jsonl", PHASE04, toxic_expected)
        s5 = status(f"{args.toxic_judged_dir}/{model}_judged.jsonl", TOXIC_JUDGE, toxic_expected, judge=True)
        toxic_rows.append({"model": model, "s4": s4, "s5": s5, "rate": rate(s5["labels"], s5["valid"])})

    print(f"ORR expected records: {len(orr_expected)}")
    print(f"Toxic expected records: {len(toxic_expected)}")
    print_section("ORR incomplete or dirty", [row for row in orr_rows if not row["s4"]["complete"] or not row["s5"]["complete"] or row["s4"]["bad"] or row["s5"]["bad"]])
    print_section("Toxic incomplete or dirty", [row for row in toxic_rows if not row["s4"]["complete"] or not row["s5"]["complete"] or row["s4"]["bad"] or row["s5"]["bad"]])
    print_response_duplicate_section("ORR exact repeated response diagnostics", orr_rows)
    print_response_duplicate_section("Toxic exact repeated response diagnostics", toxic_rows)

    orr_repair = [row["model"] for row in orr_rows if not row["s4"]["complete"] or not row["s5"]["complete"] or row["s4"]["bad"] or row["s5"]["bad"]]
    toxic_repair = [row["model"] for row in toxic_rows if not row["s4"]["complete"] or not row["s5"]["complete"] or row["s4"]["bad"] or row["s5"]["bad"]]
    print("\nORR_REPAIR_MODELS=" + " ".join(orr_repair))
    print("TOXIC_REPAIR_MODELS=" + " ".join(toxic_repair))


if __name__ == "__main__":
    main()
