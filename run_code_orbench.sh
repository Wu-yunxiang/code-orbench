#!/bin/bash
set -e

echo "============================================="
echo " Starting Code-ORbench 2026 Pipeline"
echo "============================================="

# 1. Ingest
echo "[1/6] Ingesting and Filtering Seeds..."
python dataset_builder/01_seed_ingestor.py \
    --input ../toxic_seeds/prompt.json \
    --output ./dataset/01_filtered_seeds.json

# 2. Jailbreak Mix
echo "[2/6] Mixing with Jailbreak Templates..."
python dataset_builder/02_jailbreak_mixer.py \
    --filtered ./dataset/01_filtered_seeds.json \
    --jailbreak ../toxic_seeds/jailbreak-prompt.json \
    --output ./dataset/02_mixed_seeds.json \
    --ratio 0.3

# 3. Rewrite
echo "[3/6] Task-Aware Code Rewriting..."
# Requires UNCENSORED_API_KEY to be set
python rewriter/03_code_intent_rewriter.py \
    --input ./dataset/02_mixed_seeds.json \
    --output ./dataset/03_rewritten_seeds.json

# 4. Deduplicate
echo "[4/6] Deduplicating Similar Prompts..."
python core/deduplicator.py \
    --input ./dataset/03_rewritten_seeds.json \
    --output ./dataset/04_deduped_seeds.json

# 5. Moderate
echo "[5/6] Ensemble Moderation (Filtering True Malicious)..."
# Requires OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
python moderator/04_ensemble_moderator.py \
    --input ./dataset/04_deduped_seeds.json \
    --output ./dataset/05_moderated_safe_seeds.json

# 6. Evaluate Targets
echo "[6/6] Target Evaluation (Inference & Judging)..."
# Let's run a test loop on our 2026 targets
models=("claude-4.6-opus" "claude-4.6-sonnet" "claude-3.5-sonnet" "gpt-5.3-codex-preview" "gpt-5.2-thinking" "gpt-4o" "gemini-3.1-pro-preview" "gemini-1.5-pro" "deepseek-r1" "deepseek-v3.2" "deepseek-coder-v2" "llama-4-maverick" "llama-3.1-70b" "qwen-3.5-plus" "qwen-2.5-coder-32b")

for model in "${models[@]}"; do
    echo "  -> Evaluating $model"
    python evaluator/05_run_inference.py \
        --input ./dataset/05_moderated_safe_seeds.json \
        --output-dir ./dataset/eval_outputs/ \
        --model "$model"
done

echo "  -> Running GPT-5.2-Thinking Judge..."
python evaluator/06_llm_judge.py \
    --input-dir ./dataset/eval_outputs/ \
    --output-dir ./dataset/final_judgments/

echo "============================================="
echo " Code-ORbench Pipeline Completed Successfully"
echo "============================================="
