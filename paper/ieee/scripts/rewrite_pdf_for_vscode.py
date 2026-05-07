#!/usr/bin/env python3
"""Rewrite a PDF with a classic xref table for stricter VS Code PDF viewers."""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def rewrite_pdf(src: Path, dst: Path) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for key, value in (reader.metadata or {}).items():
        if value is not None:
            try:
                writer.add_metadata({key: str(value)})
            except Exception:
                pass
    with dst.open("wb") as f:
        writer.write(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rewrite_pdf(args.input, args.output)


if __name__ == "__main__":
    main()
