#!/bin/bash
set -e

echo "============================================="
echo " Starting Code-ORbench 2026 Pipeline"
echo "============================================="

# 1. Ingest
echo "[1/5] Ingesting and Filtering Seeds..."
python3 dataset_builder/01_seed_ingestor.py \
    --input toxic_seeds/prompt.json \
    --output ./dataset/01_filtered_seeds.json

# 2. Rewrite
echo "[2/5] Task-Aware Code Rewriting..."
# Requires UNCENSORED_API_KEY to be set
python3 rewriter/02_code_intent_rewriter.py \
    --input ./dataset/01_filtered_seeds.json \
    --output ./dataset/02_rewritten_seeds.json

# 3. Deduplicate
echo "[3/5] Deduplicating Similar Prompts..."
python3 core/deduplicator.py \
    --input ./dataset/02_rewritten_seeds.json \
    --output ./dataset/03_deduped_seeds.json

# 4. Moderate
echo "[4/5] Ensemble Moderation (Filtering True Malicious)..."
# Requires OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
python3 moderator/03_ensemble_moderator.py \
    --input ./dataset/03_deduped_seeds.json \
    --output ./dataset/04_moderated_safe_seeds.json

# 5. Evaluate Targets
echo "[5/5] Target Evaluation (Inference & Judging)..."
# Let's run a test loop on our 2026 targets
models=("claude-4.6-opus" "claude-4.6-sonnet" "claude-3.5-sonnet" "gpt-5.3-codex-preview" "gpt-5.2-thinking" "gpt-4o" "gemini-3.1-pro-preview" "gemini-1.5-pro" "deepseek-r1" "deepseek-v3.2" "deepseek-coder-v2" "llama-4-maverick" "llama-3.1-70b" "qwen-3.5-plus" "qwen-2.5-coder-32b")

for model in "${models[@]}"; do
    echo "  -> Evaluating $model"
    python3 evaluator/04_run_inference.py \
        --input ./dataset/04_moderated_safe_seeds.json \
        --output-dir ./dataset/eval_outputs/ \
        --model "$model"
done

echo "  -> Running GPT-5.2-Thinking Judge..."
python3 evaluator/05_llm_judge.py \
    --input-dir ./dataset/eval_outputs/ \
    --output-dir ./dataset/final_judgments/

echo "============================================="
echo " Code-ORbench Pipeline Completed Successfully"
echo "============================================="
