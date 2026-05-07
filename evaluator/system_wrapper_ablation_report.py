#!/usr/bin/env python3
"""Summarize system prompt / safety wrapper ablation results."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ORR_REPORT = load_module("phase06_report_metrics", ROOT / "evaluator" / "06_report_metrics.py")
TOXIC_REPORT = load_module("toxic_report", ROOT / "evaluator" / "toxic_report.py")


def pct_float(text: str) -> float:
    return float(str(text).rstrip("%"))


def summarize_orr(path: Path) -> dict:
    row = ORR_REPORT.summarize_file(path)
    return {
        "valid": row["valid"],
        "refusal": row["refusal"],
        "rate": pct_float(row["over_refusal_rate"]),
    }


def summarize_toxic(path: Path) -> dict:
    row = TOXIC_REPORT.summarize_file(path)
    return {
        "valid": row["valid"],
        "refusal": row["refusal"],
        "rate": pct_float(row["toxic_rejection_rate"]),
    }


def load_mode_rows(mode: str, model: str, root: Path) -> tuple[dict, dict]:
    orr_path = root / mode / "orr" / "05_judged_refusal_intent" / f"{model}_judged.jsonl"
    toxic_path = root / mode / "toxic" / "05_judged_refusal_intent" / f"{model}_judged.jsonl"
    if not orr_path.exists():
        raise SystemExit(f"Missing ORR judged file: {orr_path}")
    if not toxic_path.exists():
        raise SystemExit(f"Missing toxic judged file: {toxic_path}")
    return summarize_orr(orr_path), summarize_toxic(toxic_path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "model",
        "family",
        "system_mode",
        "orr_valid",
        "over_refusal_rate",
        "toxic_valid",
        "toxic_prompt_refusal_rate",
        "gap_toxic_minus_orr",
        "delta_orr_vs_raw",
        "delta_toxic_vs_raw",
        "delta_gap_vs_raw",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict]) -> None:
    lines = [
        "# System Prompt / Safety Wrapper Ablation",
        "",
        "该报告比较 raw baseline、generic safety wrapper 和 defensive-code-aware wrapper 对 over-refusal rate 与 toxic-prompt refusal rate 的影响。",
        "",
        "| model | mode | ORR | TRR | gap | ΔORR | ΔTRR | Δgap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['model']}` | {row['system_mode']} | {row['over_refusal_rate']:.2f}% | "
            f"{row['toxic_prompt_refusal_rate']:.2f}% | {row['gap_toxic_minus_orr']:.2f} | "
            f"{row['delta_orr_vs_raw']:.2f} | {row['delta_toxic_vs_raw']:.2f} | "
            f"{row['delta_gap_vs_raw']:.2f} |"
        )

    modes = sorted({row["system_mode"] for row in rows if row["system_mode"] != "raw"})
    lines.extend(["", "## Mode Averages", "", "| mode | mean ΔORR | mean ΔTRR | mean Δgap |", "| --- | ---: | ---: | ---: |"])
    for mode in modes:
        subset = [row for row in rows if row["system_mode"] == mode]
        lines.append(
            f"| {mode} | {sum(row['delta_orr_vs_raw'] for row in subset) / len(subset):.2f} | "
            f"{sum(row['delta_toxic_vs_raw'] for row in subset) / len(subset):.2f} | "
            f"{sum(row['delta_gap_vs_raw'] for row in subset) / len(subset):.2f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("&", "\\&")
        .replace("%", "\\%")
    )


def display_model(model: str) -> str:
    names = {
        "claude-haiku-4-5-20251001": "claude-haiku-4-5",
        "gemini-3.1-pro-preview-thinking": "gemini-3.1-pro-thinking",
    }
    return names.get(model, model)


def write_latex_table(path: Path, rows: list[dict], models: list[str]) -> None:
    by_model_mode = {(row["model"], row["system_mode"]): row for row in rows}
    body: list[str] = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\scriptsize",
        "\\caption{System-prompt and safety-wrapper ablation on 100 \\benchmark prompts and 50 toxic-control prompts. Each cell reports ORR/TRR in percent.}",
        "\\label{tab:system_wrapper}",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Model & Raw & Generic safety & Defensive-code-aware & $\\Delta$ gap \\\\",
        "\\midrule",
    ]
    for model in models:
        raw = by_model_mode[(model, "raw")]
        generic = by_model_mode[(model, "generic_safety")]
        defensive = by_model_mode[(model, "defensive_code_aware")]
        body.append(
            f"\\texttt{{{latex_escape(display_model(model))}}} & "
            f"{raw['over_refusal_rate']:.0f}/{raw['toxic_prompt_refusal_rate']:.0f} & "
            f"{generic['over_refusal_rate']:.0f}/{generic['toxic_prompt_refusal_rate']:.0f} & "
            f"{defensive['over_refusal_rate']:.0f}/{defensive['toxic_prompt_refusal_rate']:.0f} & "
            f"{defensive['delta_gap_vs_raw']:+.0f} \\\\"
        )

    generic_rows = [row for row in rows if row["system_mode"] == "generic_safety"]
    defensive_rows = [row for row in rows if row["system_mode"] == "defensive_code_aware"]
    generic_delta_orr = sum(row["delta_orr_vs_raw"] for row in generic_rows) / len(generic_rows)
    generic_delta_toxic = sum(row["delta_toxic_vs_raw"] for row in generic_rows) / len(generic_rows)
    defensive_delta_orr = sum(row["delta_orr_vs_raw"] for row in defensive_rows) / len(defensive_rows)
    defensive_delta_toxic = sum(row["delta_toxic_vs_raw"] for row in defensive_rows) / len(defensive_rows)
    defensive_delta_gap = sum(row["delta_gap_vs_raw"] for row in defensive_rows) / len(defensive_rows)
    body.extend(
        [
            "\\midrule",
            f"Mean $\\Delta$ vs. raw & -- & {generic_delta_orr:+.2f}/{generic_delta_toxic:+.2f} & "
            f"{defensive_delta_orr:+.2f}/{defensive_delta_toxic:+.2f} & {defensive_delta_gap:+.2f} \\\\",
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table*}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="dataset/ablation/system_wrapper")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--modes", nargs="+", default=["raw", "generic_safety", "defensive_code_aware"])
    parser.add_argument("--summary-csv", default="dataset/ablation/system_wrapper/system_wrapper_ablation_summary.csv")
    parser.add_argument("--report-md", default="dataset/ablation/system_wrapper/system_wrapper_ablation_report.md")
    parser.add_argument("--latex-table")
    args = parser.parse_args()

    root = Path(args.root)
    rows = []
    raw_by_model = {}
    for model in args.models:
        raw_orr, raw_toxic = load_mode_rows("raw", model, root)
        raw_by_model[model] = {
            "orr": raw_orr["rate"],
            "toxic": raw_toxic["rate"],
            "gap": raw_toxic["rate"] - raw_orr["rate"],
        }
        for mode in args.modes:
            orr, toxic = load_mode_rows(mode, model, root)
            gap = toxic["rate"] - orr["rate"]
            raw = raw_by_model[model]
            rows.append(
                {
                    "model": model,
                    "family": TOXIC_REPORT.model_family(model),
                    "system_mode": mode,
                    "orr_valid": orr["valid"],
                    "over_refusal_rate": orr["rate"],
                    "toxic_valid": toxic["valid"],
                    "toxic_prompt_refusal_rate": toxic["rate"],
                    "gap_toxic_minus_orr": gap,
                    "delta_orr_vs_raw": orr["rate"] - raw["orr"],
                    "delta_toxic_vs_raw": toxic["rate"] - raw["toxic"],
                    "delta_gap_vs_raw": gap - raw["gap"],
                }
            )
    rows.sort(key=lambda row: (row["family"], row["model"], row["system_mode"]))
    write_csv(Path(args.summary_csv), rows)
    write_report(Path(args.report_md), rows)
    if args.latex_table:
        write_latex_table(Path(args.latex_table), rows, args.models)
    print(f"wrote system wrapper ablation report for {len(args.models)} models", flush=True)


if __name__ == "__main__":
    main()
