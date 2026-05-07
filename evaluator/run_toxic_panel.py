#!/usr/bin/env python3
"""Run aligned toxic-prompt inference and binary refusal judging."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import time
from pathlib import Path


DEFAULT_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-5.2",
    "gpt-5.3-codex",
    "gpt-5.3-codex-high",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "gemini-3-flash-preview",
    "gemini-3-flash-preview-thinking",
    "gemini-2.5-pro",
    "gemini-2.5-flash-thinking",
    "gemini-3.1-pro-preview-thinking",
    "qwen3-14b",
    "qwen3-30b-a3b-instruct-2507",
    "qwen3-235b-a22b-instruct-2507",
    "qwen3-235b-a22b-thinking-2507",
    "qwen3-coder-plus",
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


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
PHASE04 = load_module("phase04_run_inference", SCRIPT_DIR / "04_run_inference.py")
TOXIC_JUDGE = load_module("toxic_refusal_judge", SCRIPT_DIR / "toxic_refusal_judge.py")
TOXIC_REPORT = load_module("toxic_report", SCRIPT_DIR / "toxic_report.py")


def parse_models(models):
    if not models:
        return list(DEFAULT_MODELS)
    parsed = []
    for item in models:
        parsed.extend(part.strip() for part in item.split(",") if part.strip())
    return parsed or list(DEFAULT_MODELS)


def expected_record_ids(input_file, limit=None):
    records = PHASE04.select_records(PHASE04.load_records(input_file), limit)
    return {record["record_id"] for record in records}


def read_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                yield idx, json.loads(line)
            except json.JSONDecodeError:
                yield idx, None


def inference_status(path, expected_ids):
    valid_ids = set()
    seen_ids = set()
    bad_rows = 0
    duplicate_rows = 0
    total_rows = 0
    for idx, item in read_jsonl(path) or []:
        total_rows += 1
        if item is None:
            bad_rows += 1
            continue
        record_id = PHASE04.compute_record_id(item, idx)
        if record_id in seen_ids:
            duplicate_rows += 1
            continue
        seen_ids.add(record_id)
        if record_id not in expected_ids or not PHASE04.is_completed_checkpoint_item(item):
            bad_rows += 1
            continue
        valid_ids.add(record_id)
    return {
        "total_rows": total_rows,
        "valid": len(valid_ids),
        "bad_rows": bad_rows,
        "duplicate_rows": duplicate_rows,
        "missing": len(expected_ids - valid_ids),
        "complete": len(valid_ids) == len(expected_ids),
    }


def judge_status(path, expected_ids):
    valid_ids = set()
    seen_ids = set()
    bad_rows = 0
    duplicate_rows = 0
    total_rows = 0
    for idx, item in read_jsonl(path) or []:
        total_rows += 1
        if item is None:
            bad_rows += 1
            continue
        record_id = TOXIC_JUDGE.compute_record_id(item, idx)
        if record_id in seen_ids:
            duplicate_rows += 1
            continue
        seen_ids.add(record_id)
        if record_id not in expected_ids or not TOXIC_JUDGE.is_completed_judge_item(item):
            bad_rows += 1
            continue
        valid_ids.add(record_id)
    return {
        "total_rows": total_rows,
        "valid": len(valid_ids),
        "bad_rows": bad_rows,
        "duplicate_rows": duplicate_rows,
        "missing": len(expected_ids - valid_ids),
        "complete": len(valid_ids) == len(expected_ids),
    }


def summarize_judged_model(path):
    summary = TOXIC_REPORT.summarize_file(path)
    return (
        f"valid={summary['valid']}, TRR={summary['toxic_rejection_rate']}, "
        f"REFUSAL={summary['refusal']}, NON_REFUSAL={summary['non_refusal']}, "
        f"invalid={summary['invalid']}, error={summary['error']}"
    )


def run_one_model(model, expected_ids, args):
    inference_path = os.path.join(args.inference_dir, f"{model}.jsonl")
    judged_path = os.path.join(args.judged_dir, f"{model}_judged.jsonl")
    expected_n = len(expected_ids)

    print(f"\n[TOXIC_MODEL_START] {model}", flush=True)
    for round_id in range(1, args.max_rounds + 1):
        status = inference_status(inference_path, expected_ids)
        if status["complete"]:
            print(f"[TOXIC_04_COMPLETE] {model}: {status['valid']}/{expected_n}", flush=True)
            break
        print(
            f"[TOXIC_04_ROUND] {model}: round={round_id}, valid={status['valid']}/{expected_n}, "
            f"missing={status['missing']}, bad_rows={status['bad_rows']}, duplicates={status['duplicate_rows']}",
            flush=True,
        )
        PHASE04.process_inference(
            input_file=args.input,
            output_dir=args.inference_dir,
            api_key=args.api_key,
            base_url=args.base_url,
            max_workers=args.inference_workers,
            model_workers=1,
            models=[model],
            limit=args.limit,
            system_mode=args.system_mode,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            retries=args.retries,
            request_timeout=args.request_timeout,
            allow_empty_responses=False,
            empty_response_retries=args.empty_response_retries,
            allow_incomplete_responses=False,
            incomplete_response_retries=args.incomplete_response_retries,
            prune_invalid_checkpoints=True,
        )
        time.sleep(args.round_sleep)
    else:
        status = inference_status(inference_path, expected_ids)
        print(f"[TOXIC_04_INCOMPLETE] {model}: valid={status['valid']}/{expected_n}", flush=True)
        return {"model": model, "stage": "04_incomplete", "inference": status}

    for round_id in range(1, args.max_rounds + 1):
        status = judge_status(judged_path, expected_ids)
        if status["complete"]:
            print(f"[TOXIC_05_COMPLETE] {model}: {status['valid']}/{expected_n}", flush=True)
            break
        print(
            f"[TOXIC_05_ROUND] {model}: round={round_id}, valid={status['valid']}/{expected_n}, "
            f"missing={status['missing']}, bad_rows={status['bad_rows']}, duplicates={status['duplicate_rows']}",
            flush=True,
        )
        TOXIC_JUDGE.process_judging(
            input_dir=args.inference_dir,
            output_dir=args.judged_dir,
            api_key=args.api_key,
            base_url=args.base_url,
            judge_model=args.judge_model,
            max_workers=args.judge_workers,
            model_workers=1,
            temperature=args.judge_temperature,
            retries=args.judge_retries,
            request_timeout=args.request_timeout,
            models=[model],
            prune_invalid_checkpoints=True,
        )
        time.sleep(args.round_sleep)
    else:
        status = judge_status(judged_path, expected_ids)
        print(f"[TOXIC_05_INCOMPLETE] {model}: valid={status['valid']}/{expected_n}", flush=True)
        return {
            "model": model,
            "stage": "05_incomplete",
            "inference": inference_status(inference_path, expected_ids),
            "judge": status,
        }

    summary_text = summarize_judged_model(judged_path)
    print(f"[TOXIC_MODEL_DONE] {model}: {summary_text}", flush=True)
    return {
        "model": model,
        "stage": "complete",
        "inference": inference_status(inference_path, expected_ids),
        "judge": judge_status(judged_path, expected_ids),
        "summary": summary_text,
    }


def write_status_report(path, results):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    complete = [row for row in results if row["stage"] == "complete"]
    incomplete = [row for row in results if row["stage"] != "complete"]
    lines = [
        "# 同源 toxic prompts 全量评测进度",
        "",
        f"完成模型数：{len(complete)}",
        f"未完成模型数：{len(incomplete)}",
        "",
        "## 完成模型",
        "",
    ]
    if complete:
        for row in sorted(complete, key=lambda item: item["model"]):
            lines.append(f"- `{row['model']}`：{row['summary']}")
    else:
        lines.append("- 暂无")
    lines.extend(["", "## 未完成模型", ""])
    if incomplete:
        for row in sorted(incomplete, key=lambda item: item["model"]):
            inference = row.get("inference", {})
            judge = row.get("judge", {})
            lines.append(
                f"- `{row['model']}`：stage={row['stage']}, "
                f"04={inference.get('valid', 0)}, 05={judge.get('valid', 0)}"
            )
    else:
        lines.append("- 无")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dataset/toxic_aligned/01_toxic_prompts.jsonl")
    parser.add_argument("--inference-dir", default="dataset/toxic_aligned/04_inference")
    parser.add_argument("--judged-dir", default="dataset/toxic_aligned/05_judged")
    parser.add_argument("--metrics-output", default="dataset/toxic_aligned/06_toxic_metrics_report.md")
    parser.add_argument("--status-output", default="dataset/toxic_aligned/toxic_full_eval_status.md")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--parallel-models", type=int, default=4)
    parser.add_argument("--inference-workers", type=int, default=24)
    parser.add_argument("--judge-workers", type=int, default=24)
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--round-sleep", type=float, default=1.0)
    parser.add_argument("--system-mode", choices=sorted(PHASE04.SYSTEM_PROMPTS.keys()), default="raw")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--judge-temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--judge-retries", type=int, default=8)
    parser.add_argument("--empty-response-retries", type=int, default=12)
    parser.add_argument("--incomplete-response-retries", type=int, default=12)
    parser.add_argument("--request-timeout", type=float, default=300.0)
    parser.add_argument("--judge-model", default="gpt-5.2")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "dummy"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    args = parser.parse_args()

    models = parse_models(args.models)
    expected_ids = expected_record_ids(args.input, args.limit)
    os.makedirs(args.inference_dir, exist_ok=True)
    os.makedirs(args.judged_dir, exist_ok=True)

    print(f"Selected toxic models: {', '.join(models)}", flush=True)
    print(f"Expected toxic records per model: {len(expected_ids)}", flush=True)
    print(
        f"Concurrency: parallel_models={args.parallel_models}, "
        f"inference_workers={args.inference_workers}, judge_workers={args.judge_workers}",
        flush=True,
    )

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.parallel_models)) as executor:
        futures = {executor.submit(run_one_model, model, expected_ids, args): model for model in models}
        for future in concurrent.futures.as_completed(futures):
            model = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"model": model, "stage": "exception", "error": str(exc)}
                print(f"[TOXIC_MODEL_EXCEPTION] {model}: {exc}", flush=True)
            results.append(result)
            write_status_report(args.status_output, results)

    complete_count = sum(1 for row in results if row["stage"] == "complete")
    if complete_count:
        TOXIC_REPORT.process_metrics(args.judged_dir, args.metrics_output)
    write_status_report(args.status_output, results)
    print(f"[TOXIC_RUN_DONE] complete={complete_count}/{len(results)}", flush=True)


if __name__ == "__main__":
    main()
