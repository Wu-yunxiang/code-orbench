#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

mkdir -p figures
mkdir -p tables
python3 ../scripts/make_figures.py
python3 ../scripts/prompt_diversity.py \
  --input ../../../dataset/full_all/03c_selected_records.jsonl \
  --summary-csv ../../../dataset/validation/prompt_diversity_summary.csv \
  --report-md ../../../dataset/validation/prompt_diversity_report.md \
  --figure figures/prompt_diversity.pdf >/dev/null
if [[ -f ../../../dataset/validation/judge_robustness_gemini31.jsonl ]]; then
  python3 ../scripts/judge_robustness.py \
    --summarize-only \
    --root ../../../dataset/temperature_sweep \
    --output-jsonl ../../../dataset/validation/judge_robustness_gemini31.jsonl \
    --summary-csv ../../../dataset/validation/judge_robustness_summary.csv \
    --report-md ../../../dataset/validation/judge_robustness_report.md >/dev/null
fi
if [[ -f ../../../dataset/validation/qwen_coderplus_judge_robustness_150/qwen3-coder-plus_gemini31_screening.jsonl ]]; then
  python3 ../scripts/build_representative_judge_robustness.py >/dev/null
fi
if [[ -d ../../../dataset/ablation/system_wrapper ]]; then
  python3 ../../../evaluator/system_wrapper_ablation_report.py \
    --root ../../../dataset/ablation/system_wrapper \
    --models claude-haiku-4-5-20251001 gemini-3.1-pro-preview-thinking deepseek-v3.2 glm-5 gpt-5.2 grok-4 llama-3.3-70b qwen3-coder-plus \
    --modes raw generic_safety defensive_code_aware \
    --summary-csv ../../../dataset/ablation/system_wrapper/system_wrapper_ablation_summary.csv \
    --report-md ../../../dataset/ablation/system_wrapper/system_wrapper_ablation_report.md \
    --latex-table tables/system_wrapper_ablation_table.tex >/dev/null
fi
python3 ../../../evaluator/toxic_report.py \
  --input-dir ../../../dataset/toxic_aligned/05_judged_refusal_intent \
  --output ../../../dataset/toxic_aligned/06_toxic_metrics_report_refusal_intent.md \
  --orr-judged-dirs ../../../dataset/full_all/05_judged_refusal_intent ../../../dataset/full_all/05_judged_expanded_refusal_intent \
  --comparison-csv ../../../dataset/toxic_aligned/07_orr_toxic_comparison_refusal_intent.csv \
  --comparison-md ../../../dataset/toxic_aligned/07_orr_toxic_comparison_refusal_intent.md \
  --figure-dir figures >/dev/null

if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf main.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
  bibtex main
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
  pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
elif [[ -x ../../../.tools/tectonic/tectonic ]]; then
  ../../../.tools/tectonic/tectonic -X compile \
    --synctex \
    --bundle https://data1.fullyjustified.net/tlextras-2022.0r0.tar \
    main.tex
else
  echo "No LaTeX compiler found. Install TeX Live/MacTeX or use the project tectonic binary." >&2
  exit 1
fi

if [[ -f main.pdf && -f ../../ieee/scripts/rewrite_pdf_for_vscode.py ]]; then
  cp main.pdf main_latex_original.pdf
  python3 ../../ieee/scripts/rewrite_pdf_for_vscode.py main_latex_original.pdf main.pdf
fi
