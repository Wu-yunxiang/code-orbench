#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf main.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
  bibtex main
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
elif [[ -x ../../.tools/tectonic/tectonic ]]; then
  ../../.tools/tectonic/tectonic -X compile \
    --synctex \
    --bundle https://data1.fullyjustified.net/tlextras-2022.0r0.tar \
    main.tex
else
  echo "No LaTeX compiler found. Install TeX Live/MacTeX or run from VS Code with LaTeX Workshop." >&2
  exit 1
fi

if [[ -f main.pdf ]]; then
  cp main.pdf main_tectonic_original.pdf
  python3 scripts/rewrite_pdf_for_vscode.py main_tectonic_original.pdf main.pdf
fi
