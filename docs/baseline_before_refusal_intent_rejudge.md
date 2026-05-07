# 新版05重判前基线快照

该文件记录旧版 05 fulfillment/refusal 标准下的结果，用于和新版 refusal-intent 标准对照。

模型数: 35

| 模型 | 家族 | 旧 ORR | 旧 TRR | 旧 TRR-ORR |
| --- | --- | ---: | ---: | ---: |
| `claude-haiku-4-5-20251001` | Claude | 15.82% | 34.19% | 18.37 |
| `claude-opus-4-6` | Claude | 16.07% | 52.99% | 36.92 |
| `claude-sonnet-4-6` | Claude | 31.12% | 31.62% | 0.50 |
| `deepseek-v3.2` | DeepSeek | 3.83% | 50.43% | 46.60 |
| `deepseek-v3.2-thinking` | DeepSeek | 5.36% | 52.99% | 47.63 |
| `deepseek-r1` | DeepSeek | 74.23% | 8.55% | -65.69 |
| `glm-4.5-air` | GLM | 0.51% | 11.11% | 10.60 |
| `glm-4.7` | GLM | 18.37% | 63.25% | 44.88 |
| `glm-5` | GLM | 19.64% | 64.10% | 44.46 |
| `glm-4-32b-0414` | GLM | 41.33% | 40.17% | -1.16 |
| `gpt-4o` | GPT | 20.66% | 51.28% | 30.62 |
| `gpt-5.2` | GPT | 40.31% | 76.92% | 36.62 |
| `gpt-5.3-codex` | GPT | 47.70% | 73.50% | 25.80 |
| `gpt-5.3-codex-high` | GPT | 56.63% | 78.63% | 22.00 |
| `gpt-4o-mini` | GPT | 84.69% | 47.01% | -37.69 |
| `gemini-3-flash-preview-thinking` | Gemini | 13.78% | 59.83% | 46.05 |
| `gemini-3.1-pro-preview-thinking` | Gemini | 16.33% | 68.38% | 52.05 |
| `gemini-3-flash-preview` | Gemini | 17.86% | 45.30% | 27.44 |
| `gemini-2.5-flash-thinking` | Gemini | 25.00% | 31.62% | 6.62 |
| `gemini-2.5-pro` | Gemini | 28.57% | 45.30% | 16.73 |
| `grok-3` | Grok | 20.92% | 52.14% | 31.22 |
| `grok-3-reasoner` | Grok | 21.17% | 55.56% | 34.38 |
| `grok-3-reasoning` | Grok | 21.43% | 52.99% | 31.56 |
| `grok-4` | Grok | 53.32% | 47.01% | -6.31 |
| `llama-3.3-70b` | Llama | 0.00% | 6.84% | 6.84 |
| `llama-4-maverick-17b-128e-instruct` | Llama | 0.00% | 12.82% | 12.82 |
| `llama3.1-8b` | Llama | 3.83% | 26.50% | 22.67 |
| `qwen2.5-14b-instruct` | Qwen | 1.02% | 39.32% | 38.30 |
| `qwen3-14b` | Qwen | 4.59% | 37.61% | 33.02 |
| `qwen3-30b-a3b-instruct-2507` | Qwen | 39.29% | 58.12% | 18.83 |
| `qwen3.5-397b-a17b` | Qwen | 72.96% | 74.36% | 1.40 |
| `qwen3-235b-a22b-instruct-2507` | Qwen | 76.28% | 67.52% | -8.75 |
| `qwen3-coder-plus` | Qwen | 77.30% | 78.63% | 1.34 |
| `qwen3-235b-a22b-thinking-2507` | Qwen | 77.55% | 67.52% | -10.03 |

旧结果文件已复制到:
- `dataset/full_all/baseline_before_refusal_intent_rejudge/`
- `dataset/toxic_aligned/baseline_before_refusal_intent_rejudge/`
