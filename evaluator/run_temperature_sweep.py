#!/usr/bin/env python3
"""Run ORR/TRR temperature sweep on the prepared aligned samples."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPRESENTATIVE_MODELS = [
    "claude-sonnet-4-6",
    "deepseek-v3.2-thinking",
    "glm-4-32b-0414",
    "gpt-4o-mini",
    "gemini-3-flash-preview-thinking",
    "grok-4",
    "llama3.1-8b",
    "qwen3.5-397b-a17b",
]


def parse_csv_list(value: str) -> list[str]:
    return [part.strip() for part in value.replace(" ", ",").split(",") if part.strip()]


def temp_slug(value: float) -> str:
    return f"t{value:.1f}".replace(".", "_")


def run_command(cmd: list[str], env: dict[str, str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dataset/temperature_sweep")
    parser.add_argument("--orr-input", default="dataset/temperature_sweep/01_orr_sample_100.jsonl")
    parser.add_argument("--toxic-input", default="dataset/temperature_sweep/01_toxic_sample_50.jsonl")
    parser.add_argument("--temperatures", default="0,0.2,0.4,0.6,0.8,1.0")
    parser.add_argument("--models", nargs="+", default=REPRESENTATIVE_MODELS)
    parser.add_argument("--skip-orr", action="store_true")
    parser.add_argument("--skip-toxic", action="store_true")
    parser.add_argument("--parallel-models", type=int, default=4)
    parser.add_argument("--inference-workers", type=int, default=16)
    parser.add_argument("--judge-workers", type=int, default=16)
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--judge-retries", type=int, default=8)
    parser.add_argument("--empty-response-retries", type=int, default=12)
    parser.add_argument("--incomplete-response-retries", type=int, default=12)
    parser.add_argument("--request-timeout", type=float, default=300.0)
    parser.add_argument("--judge-model", default="gpt-5.2")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "dummy"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    args = parser.parse_args()

    temperatures = [float(item) for item in parse_csv_list(args.temperatures)]
    models = parse_csv_list(" ".join(args.models))
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["API_KEY"] = args.api_key
    env["BASE_URL"] = args.base_url

    for temperature in temperatures:
        slug = temp_slug(temperature)
        temp_root = root / slug
        print(f"\n=== Temperature {temperature:.1f} ({slug}) ===", flush=True)

        if not args.skip_orr:
            run_command(
                [
                    sys.executable,
                    "evaluator/run_full_panel.py",
                    "--input",
                    args.orr_input,
                    "--inference-dir",
                    str(temp_root / "orr" / "04_inference"),
                    "--judged-dir",
                    str(temp_root / "orr" / "05_judged_refusal_intent"),
                    "--metrics-output",
                    str(temp_root / "orr" / "06_metrics_report.md"),
                    "--status-output",
                    str(temp_root / "orr" / "status.md"),
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
                    str(temperature),
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
                    args.judge_model,
                ],
                env=env,
            )

        if not args.skip_toxic:
            run_command(
                [
                    sys.executable,
                    "evaluator/run_toxic_panel.py",
                    "--input",
                    args.toxic_input,
                    "--inference-dir",
                    str(temp_root / "toxic" / "04_inference"),
                    "--judged-dir",
                    str(temp_root / "toxic" / "05_judged_refusal_intent"),
                    "--metrics-output",
                    str(temp_root / "toxic" / "06_toxic_metrics_report.md"),
                    "--status-output",
                    str(temp_root / "toxic" / "status.md"),
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
                    str(temperature),
                    "--judge-temperature",
                    "0.0",
                    "--max-tokens",
                    "1800",
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
                    "--judge-model",
                    args.judge_model,
                ],
                env=env,
            )

    print("\nTemperature sweep run complete. Generate aggregate report with evaluator/temperature_sweep_report.py", flush=True)


if __name__ == "__main__":
    main()
