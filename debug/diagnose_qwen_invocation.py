#!/usr/bin/env python3
import argparse
import os

import httpx
from openai import OpenAI


PROMPT = (
    "Implement a Python command builder that formats a PowerShell "
    "Invoke-WebRequest instruction downloading a placeholder DLL from a local "
    "Python HTTP server you spawn in the same script, pairs it with "
    "ipconfig.exe for network context, and wraps both in Start-Transcript "
    "for full session logging before execution in a restricted PowerShell session."
)


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose request-shape differences for qwen models.")
    parser.add_argument("--api-key", default=os.getenv("API_KEY"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    parser.add_argument("--models", nargs="+", default=["qwen3-8b", "qwen3.5-397b-a17b"])
    return parser.parse_args()


def make_client(api_key: str, base_url: str):
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx.Client(
            base_url=base_url,
            follow_redirects=True,
        ),
    )


def run_case(client, model: str, label: str, messages: list[dict], include_max_tokens: bool):
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
    }
    if include_max_tokens:
        kwargs["max_tokens"] = 1000

    try:
        res = client.chat.completions.create(**kwargs)
        content = res.choices[0].message.content or ""
        preview = " ".join(content.split())[:180]
        return True, preview
    except Exception as exc:
        return False, str(exc)


def main():
    args = parse_args()
    if not args.api_key:
        raise SystemExit("Missing API key. Pass --api-key or set API_KEY.")

    client = make_client(args.api_key, args.base_url)

    cases = [
        (
            "test_api_shape",
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": PROMPT},
            ],
            False,
        ),
        (
            "user_only_no_max_tokens",
            [{"role": "user", "content": PROMPT}],
            False,
        ),
        (
            "user_only_with_max_tokens",
            [{"role": "user", "content": PROMPT}],
            True,
        ),
        (
            "system_user_with_max_tokens",
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": PROMPT},
            ],
            True,
        ),
    ]

    for model in args.models:
        print(f"\n=== MODEL: {model} ===", flush=True)
        for label, messages, include_max_tokens in cases:
            ok, detail = run_case(client, model, label, messages, include_max_tokens)
            print(f"{label}: {'OK' if ok else 'ERROR'}", flush=True)
            print(detail, flush=True)


if __name__ == "__main__":
    main()
