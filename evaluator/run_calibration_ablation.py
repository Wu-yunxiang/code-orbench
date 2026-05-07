#!/usr/bin/env python3
"""Run and summarize the 03B calibration ablation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


BASE_MODELS = [
    "claude-haiku-4-5-20251001",
    "deepseek-v3.2",
    "glm-5",
    "gpt-5.2",
    "gemini-3.1-pro-preview-thinking",
    "grok-4",
    "llama-3.3-70b",
]


def parse_models(values: list[str] | None) -> list[str]:
    if not values:
        return list(BASE_MODELS)
    models: list[str] = []
    for value in values:
        models.extend(part.strip() for part in value.replace(",", " ").split() if part.strip())
    return models


def selected_qwen(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return "qwen3.5-397b-a17b"
    value = p.read_text(encoding="utf-8").strip()
    return value or "qwen3.5-397b-a17b"


def run_command(cmd: list[str], env: dict[str, str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dataset/ablation/calibration")
    parser.add_argument("--input", default="dataset/full_all/03b_rejected_records.jsonl")
    parser.add_argument("--qwen-selection", default="dataset/validation/qwen_judge_screening/selected_qwen_model.txt")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--include-qwen", action="store_true", default=True)
    parser.add_argument("--parallel-models", type=int, default=4)
    parser.add_argument("--inference-workers", type=int, default=24)
    parser.add_argument("--judge-workers", type=int, default=24)
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--judge-retries", type=int, default=8)
    parser.add_argument("--empty-response-retries", type=int, default=12)
    parser.add_argument("--incomplete-response-retries", type=int, default=12)
    parser.add_argument("--request-timeout", type=float, default=300.0)
    parser.add_argument("--api-key", default=os.getenv("API_KEY"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    args = parser.parse_args()

    models = parse_models(args.models)
    qwen = selected_qwen(args.qwen_selection)
    if args.include_qwen and qwen not in models:
        models.append(qwen)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if args.api_key:
        env["API_KEY"] = args.api_key
    env["BASE_URL"] = args.base_url

    inference_dir = root / "04_inference_rejected"
    judged_dir = root / "05_judged_rejected_refusal_intent"
    run_command(
        [
            sys.executable,
            "evaluator/run_full_panel.py",
            "--input",
            args.input,
            "--inference-dir",
            str(inference_dir),
            "--judged-dir",
            str(judged_dir),
            "--metrics-output",
            str(root / "06_metrics_rejected.md"),
            "--status-output",
            str(root / "status_rejected.md"),
            "--models",
            *models,
            "--parallel-models",
            str(args.parallel_models),
            "--inference-workers",
            str(args.inference_workers),
            "--judge-workers",
            str(args.judge_workers),
            "--max-rounds",
            str(args.max_rounds),
            "--temperature",
            "0.0",
            "--judge-temperature",
            "0.0",
            "--max-tokens",
            "2200",
            "--retries",
            str(args.retries),
            "--judge-retries",
            str(args.judge_retries),
            "--empty-response-retries",
            str(args.empty_response_retries),
            "--incomplete-response-retries",
            str(args.incomplete_response_retries),
            "--request-timeout",
            str(args.request_timeout),
            "--judge-mode",
            "llm",
            "--judge-model",
            "gpt-5.2",
        ],
        env=env,
    )
    run_command(
        [
            sys.executable,
            "evaluator/calibration_ablation_report.py",
            "--models",
            *models,
            "--rejected-judged-dir",
            str(judged_dir),
            "--summary-csv",
            str(root / "calibration_ablation_summary.csv"),
            "--report-md",
            str(root / "calibration_ablation_report.md"),
        ],
        env=env,
    )


if __name__ == "__main__":
    main()
