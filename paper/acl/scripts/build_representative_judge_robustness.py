#!/usr/bin/env python3
"""Build the representative independent-judge validation table.

The original validation run used qwen3.5-397b-a17b as the Qwen representative.
After Qwen screening, qwen3-coder-plus is the stable Qwen representative. This
script keeps the archived rows for the other representative models, normalizes
the qwen3-coder-plus screening rows, and regenerates the same summary/report
format used by judge_robustness.py.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


JR = load_module("judge_robustness", Path(__file__).resolve().with_name("judge_robustness.py"))


def normalize_qwen_row(row: dict, model: str) -> dict:
    split = row.get("split")
    record_id = row.get("record_id")
    return {
        "task_id": f"{split}|{model}|{record_id}",
        "split": split,
        "target_model": model,
        "record_id": record_id,
        "source_pid": row.get("source_pid") or row.get("pid"),
        "source_category": row.get("source_category") or row.get("malicious_category") or row.get("category"),
        "prompt_family": row.get("prompt_family"),
        "main_judge_model": row.get("main_judge_model", "gpt-5.2"),
        "main_label": row.get("main_label"),
        "main_reasoning": row.get("main_reasoning"),
        "prompt": row.get("prompt") or row.get("rewritten_prompt"),
        "target_response": row.get("target_response"),
        "independent_judge_model": row.get("independent_judge_model"),
        "independent_label": row.get("independent_label"),
        "independent_reasoning": row.get("independent_reasoning"),
        "agreement": row.get("agreement"),
        "success": row.get("success"),
        "attempts": row.get("attempts"),
        "repair_attempts": row.get("repair_attempts"),
        "label_only_repair": row.get("label_only_repair"),
        "latency_sec": row.get("latency_sec"),
        "error": row.get("error"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-jsonl", default="dataset/validation/judge_robustness_gemini31.jsonl")
    parser.add_argument(
        "--qwen-jsonl",
        default="dataset/validation/qwen_coderplus_judge_robustness_150/qwen3-coder-plus_gemini31_screening.jsonl",
    )
    parser.add_argument("--old-qwen-model", default="qwen3.5-397b-a17b")
    parser.add_argument("--new-qwen-model", default="qwen3-coder-plus")
    parser.add_argument("--output-jsonl", default="dataset/validation/judge_robustness_gemini31_representative.jsonl")
    parser.add_argument("--summary-csv", default="dataset/validation/judge_robustness_representative_summary.csv")
    parser.add_argument("--report-md", default="dataset/validation/judge_robustness_representative_report.md")
    args = parser.parse_args()

    base_rows = [
        row
        for row in JR.read_jsonl(ROOT / args.base_jsonl)
        if row.get("target_model") != args.old_qwen_model
        and row.get("independent_label") in JR.VALID_LABELS
        and row.get("main_label") in JR.VALID_LABELS
    ]
    qwen_rows = [
        normalize_qwen_row(row, args.new_qwen_model)
        for row in JR.read_jsonl(ROOT / args.qwen_jsonl)
        if row.get("independent_label") in JR.VALID_LABELS and row.get("main_label") in JR.VALID_LABELS
    ]
    if len(qwen_rows) != 150:
        raise SystemExit(f"Expected 150 qwen rows, found {len(qwen_rows)} at {args.qwen_jsonl}")

    rows = base_rows + qwen_rows
    rows.sort(key=lambda row: (str(row.get("target_model")), str(row.get("split")), str(row.get("record_id"))))
    JR.write_jsonl(ROOT / args.output_jsonl, rows)
    summary_rows = JR.make_summary_rows(rows)
    JR.write_summary_csv(ROOT / args.summary_csv, summary_rows)
    JR.write_report(ROOT / args.report_md, rows, summary_rows, expected_total=len(rows))
    valid = sum(1 for row in rows if row.get("independent_label") in JR.VALID_LABELS)
    agreement = sum(1 for row in rows if row.get("agreement") and row.get("independent_label") in JR.VALID_LABELS)
    print(f"wrote {len(rows)} rows, valid={valid}, agreement={agreement}/{valid if valid else 0}", flush=True)


if __name__ == "__main__":
    main()
