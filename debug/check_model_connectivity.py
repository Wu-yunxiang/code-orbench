#!/usr/bin/env python3
"""Batch connectivity smoke test for OpenAI-compatible chat APIs."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path

import httpx
from openai import OpenAI


DEFAULT_PROMPT = (
    "Reply with one short sentence confirming that you can answer benign code questions."
)


def parse_models(values):
    models = []
    for value in values or []:
        models.extend(x.strip() for x in value.split(",") if x.strip())
    return models


def compact_error(exc: Exception) -> str:
    text = str(exc).replace("\n", " ").strip()
    # Avoid writing extremely long provider traces into reports.
    return text[:500]


def check_one(model: str, api_key: str, base_url: str, prompt: str, timeout: int, max_tokens: int):
    start = time.time()
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=httpx.Client(base_url=base_url, follow_redirects=True, timeout=timeout),
    )
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=max_tokens,
        )
        content = completion.choices[0].message.content
        content = "" if content is None else str(content)
        return {
            "model": model,
            "ok": bool(content.strip()),
            "empty": not bool(content.strip()),
            "latency_sec": round(time.time() - start, 2),
            "response_preview": content.strip()[:160],
            "error": None,
        }
    except Exception as exc:
        return {
            "model": model,
            "ok": False,
            "empty": False,
            "latency_sec": round(time.time() - start, 2),
            "response_preview": "",
            "error": compact_error(exc),
        }


def write_reports(results, output_jsonl: Path, output_md: Path):
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    ok_rows = [r for r in results if r["ok"]]
    fail_rows = [r for r in results if not r["ok"]]
    lines = [
        "# 模型连通性 Smoke Test",
        "",
        f"- total: {len(results)}",
        f"- ok: {len(ok_rows)}",
        f"- failed_or_empty: {len(fail_rows)}",
        "",
        "| model | status | latency_sec | note |",
        "| --- | --- | ---: | --- |",
    ]
    for row in results:
        status = "OK" if row["ok"] else ("EMPTY" if row["empty"] else "FAIL")
        note = row["response_preview"] if row["ok"] else (row["error"] or "empty response")
        note = note.replace("|", "\\|")
        lines.append(f"| `{row['model']}` | {status} | {row['latency_sec']} | {note} |")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--api-key", default=os.getenv("API_KEY"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=40)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-jsonl", default="dataset/model_connectivity/model_connectivity.jsonl")
    parser.add_argument("--output-md", default="dataset/model_connectivity/model_connectivity.md")
    args = parser.parse_args()

    models = parse_models(args.models)
    if not models:
        raise SystemExit("No models provided.")
    if not args.api_key:
        raise SystemExit("Missing API key. Pass --api-key or set API_KEY.")

    results_by_model = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                check_one,
                model,
                args.api_key,
                args.base_url,
                args.prompt,
                args.timeout,
                args.max_tokens,
            ): model
            for model in models
        }
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            results_by_model[row["model"]] = row
            status = "OK" if row["ok"] else ("EMPTY" if row["empty"] else "FAIL")
            print(f"{status}\t{row['model']}\t{row['latency_sec']}s", flush=True)

    ordered = [results_by_model[m] for m in models]
    write_reports(ordered, Path(args.output_jsonl), Path(args.output_md))


if __name__ == "__main__":
    main()
