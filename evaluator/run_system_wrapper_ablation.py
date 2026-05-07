#!/usr/bin/env python3
"""Run system prompt / safety wrapper ablation on fixed validation samples."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
import json


BASE_MODELS = [
    "claude-haiku-4-5-20251001",
    "gemini-3.1-pro-preview-thinking",
    "deepseek-v3.2",
    "glm-5",
    "gpt-5.2",
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


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sample_ids(path: str) -> list[str]:
    return [str(row["record_id"]) for row in read_jsonl(Path(path))]


def find_judged_file(model: str, dirs: list[Path]) -> Path:
    for directory in dirs:
        path = directory / f"{model}_judged.jsonl"
        if path.exists():
            return path
    raise FileNotFoundError(f"Missing full judged file for {model}")


def write_raw_subset(root: Path, model: str, args: argparse.Namespace) -> None:
    sources = [
        (
            "orr",
            sample_ids(args.orr_input),
            find_judged_file(
                model,
                [
                    Path("dataset/full_all/05_judged_refusal_intent"),
                    Path("dataset/full_all/05_judged_expanded_refusal_intent"),
                ],
            ),
            root / "raw" / "orr" / "05_judged_refusal_intent" / f"{model}_judged.jsonl",
        ),
        (
            "toxic",
            sample_ids(args.toxic_input),
            find_judged_file(model, [Path("dataset/toxic_aligned/05_judged_refusal_intent")]),
            root / "raw" / "toxic" / "05_judged_refusal_intent" / f"{model}_judged.jsonl",
        ),
    ]
    for split, ids, source_path, output_path in sources:
        rows_by_id = {str(row.get("record_id")): row for row in read_jsonl(source_path)}
        missing = [record_id for record_id in ids if record_id not in rows_by_id]
        if missing:
            raise KeyError(f"{model} raw {split} baseline missing {len(missing)} sample ids; first={missing[0]}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for record_id in ids:
                f.write(json.dumps(rows_by_id[record_id], ensure_ascii=False) + "\n")


def run_mode(args: argparse.Namespace, env: dict[str, str], root: Path, mode: str, models: list[str]) -> None:
    mode_root = root / mode
    if mode == "raw":
        for model in models:
            write_raw_subset(root, model, args)
        return
    else:
        run_models = models

    run_command(
        [
            sys.executable,
            "evaluator/run_full_panel.py",
            "--input",
            args.orr_input,
            "--inference-dir",
            str(mode_root / "orr" / "04_inference"),
            "--judged-dir",
            str(mode_root / "orr" / "05_judged_refusal_intent"),
            "--metrics-output",
            str(mode_root / "orr" / "06_metrics_report.md"),
            "--status-output",
            str(mode_root / "orr" / "status.md"),
            "--models",
            *run_models,
            "--parallel-models",
            str(args.parallel_models),
            "--inference-workers",
            str(args.inference_workers),
            "--judge-workers",
            str(args.judge_workers),
            "--max-rounds",
            str(args.max_rounds),
            "--system-mode",
            mode,
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
            "evaluator/run_toxic_panel.py",
            "--input",
            args.toxic_input,
            "--inference-dir",
            str(mode_root / "toxic" / "04_inference"),
            "--judged-dir",
            str(mode_root / "toxic" / "05_judged_refusal_intent"),
            "--metrics-output",
            str(mode_root / "toxic" / "06_toxic_metrics_report.md"),
            "--status-output",
            str(mode_root / "toxic" / "status.md"),
            "--models",
            *run_models,
            "--parallel-models",
            str(args.parallel_models),
            "--inference-workers",
            str(args.inference_workers),
            "--judge-workers",
            str(args.judge_workers),
            "--max-rounds",
            str(args.max_rounds),
            "--system-mode",
            mode,
            "--temperature",
            "0.0",
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
            "gpt-5.2",
        ],
        env=env,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dataset/ablation/system_wrapper")
    parser.add_argument("--orr-input", default="dataset/temperature_sweep/01_orr_sample_100.jsonl")
    parser.add_argument("--toxic-input", default="dataset/temperature_sweep/01_toxic_sample_50.jsonl")
    parser.add_argument("--qwen-selection", default="dataset/validation/qwen_judge_screening/selected_qwen_model.txt")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--include-qwen", action="store_true", default=True)
    parser.add_argument("--modes", nargs="+", default=["raw", "generic_safety", "defensive_code_aware"])
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

    for mode in args.modes:
        run_mode(args, env, root, mode, models)
    run_command(
        [
            sys.executable,
            "evaluator/system_wrapper_ablation_report.py",
            "--root",
            str(root),
            "--models",
            *models,
            "--modes",
            *args.modes,
            "--summary-csv",
            str(root / "system_wrapper_ablation_summary.csv"),
            "--report-md",
            str(root / "system_wrapper_ablation_report.md"),
        ],
        env=env,
    )


if __name__ == "__main__":
    main()
