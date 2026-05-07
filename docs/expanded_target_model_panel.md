# 扩展评测模型面板

## 当前结论

`dataset/full_all/03c_selected_records.jsonl` 已固定为 392 条，后续模型只进入 04/05/06 评测层，不参与 benchmark 生成或筛选。

2026-05-03 的连通性测试显示：GPT/OpenAI、Claude、Gemini、Qwen、DeepSeek、Llama、GLM、Grok 均有可用模型；Mistral 族尝试多个别名后均不可用，因此从主论文评测面板中取消，避免把路由不可用误解释为模型拒绝行为。

## 已完成的 9 个模型

这些结果已经在 392 条固定 benchmark 上完成 04/05/06：

| 模型 | ORR | 说明 |
| --- | ---: | --- |
| `qwen3-14b` | 4.59% | Qwen 较小模型。 |
| `claude-haiku-4-5-20251001` | 15.82% | Claude 小模型。 |
| `gemini-3-flash-preview` | 17.86% | Gemini Flash；03B calibration-overlap。 |
| `gpt-4o` | 20.66% | OpenAI 强基线。 |
| `qwen3-30b-a3b-instruct-2507` | 39.29% | Qwen 中等 MoE；03B calibration-overlap。 |
| `qwen3-235b-a22b-instruct-2507` | 76.28% | Qwen 大模型 instruct。 |
| `qwen3-coder-plus` | 77.30% | Qwen 代码专用模型。 |
| `qwen3-235b-a22b-thinking-2507` | 77.55% | Qwen 大模型 thinking。 |
| `gpt-4o-mini` | 84.69% | OpenAI 小模型；03B calibration-overlap。 |

## 本轮新增全量评测模型

以下模型已通过连通性检查，进入扩展全量评测。每个模型要求 04 阶段 392/392 非空、非截断成功，05 阶段 392/392 有效二分类 judge 结果，否则不进入完整指标。

| 模型族 | 新增模型 | 选入原因 |
| --- | --- | --- |
| GPT/OpenAI | `gpt-5.2` | 用户指定；强 GPT 主力模型，但与 05 judge 重叠，论文中需标注。 |
| GPT/OpenAI | `gpt-5.3-codex` | `gpt-5.2-codex` 不可用后的代码专用替代；smoke 稳定。 |
| GPT/OpenAI | `gpt-5.3-codex-high` | 代码专用高能力/高推理设置；已有部分进度，继续保留。 |
| Claude | `claude-sonnet-4-6` | 用户指定；Claude 中高能力主力模型。 |
| Claude | `claude-opus-4-6` | 用户指定；Claude 旗舰模型，成本较高但质量重要。 |
| Gemini | `gemini-3-flash-preview-thinking` | 可连通 Gemini thinking 变体；已完成 04/05。 |
| Qwen | `qwen2.5-14b-instruct` | 用户指定；补充旧代/较小 Qwen。 |
| Qwen | `qwen3.5-397b-a17b` | 用户指定；补充超大 Qwen。 |
| DeepSeek | `deepseek-r1` | 用户指定；DeepSeek reasoning 系列。 |
| DeepSeek | `deepseek-v3.2` | 用户指定；DeepSeek 新通用模型。 |
| DeepSeek | `deepseek-v3.2-thinking` | 用户指定；DeepSeek thinking 变体，03A verifier-overlap 需标注。 |
| Llama | `llama3.1-8b` | 当前保留的小 Llama 代表模型，用于替代不稳定旧别名。 |
| Llama | `llama-3.3-70b` | `llama2-70b`、`llama3-70b` 不可用后的大 Llama 替代。 |
| Llama | `llama-4-maverick-17b-128e-instruct` | 修正用户列表中的拼写后可连通；新一代 Llama 4。 |
| GLM | `glm-4-32b-0414` | 用户指定；GLM 4 系列。 |
| GLM | `glm-4.5-air` | `glm-4.5` 不可用后的可连通 GLM 4.5 变体。 |
| GLM | `glm-4.7` | 补充 GLM 中新版本；是否继续跑待确认。 |
| GLM | `glm-5` | 用户指定；GLM 5 通用模型。 |
| Grok | `grok-3` | 用户指定；Grok 3 通用模型。 |
| Grok | `grok-3-reasoner` | `grok-3-mini` 不可用后的 reasoning 替代。 |
| Grok | `grok-3-reasoning` | Grok reasoning 变体；是否继续跑待确认。 |
| Grok | `grok-4` | `grok-4.2` 不可用后的可连通 Grok 4 替代。 |

## 不进入主评测的模型

| 模型或模型族 | 处理方式 | 原因 |
| --- | --- | --- |
| Mistral 全族 | 取消主评测 | `mistral-large`、`mistral-small`、latest、7B、Mixtral 等均未连通。 |
| `gpt-5.2-codex` | 不跑 | 当前 API 路由不可用，使用 `gpt-5.3-codex` 与 `gpt-5.3-codex-high` 替代。 |
| `gpt-5-codex` | 暂不放主评测 | 连通但 20 条 smoke 中有 4 条坏响应，可作为后续补充模型。 |
| `claude-sonnet-4-20250514`、`claude-3-sonnet-20240229` | 不跑 | 当前 API 路由不可用。 |
| `gemini-3-pro-preview`、`gemini-2.5-flash`、`gemini-1.5-pro`、`gemini-1.5-flash` | 不跑 | 当前 API 路由不可用或超时。 |
| `deepseek-coder` | 不跑 | 当前 API 路由不可用。 |
| `llama2-70b`、`llama-3.1-405b` | 不跑 | 当前 API 路由不可用。 |
| `glm-4.5`、`glm-5-thinking` | 不跑 | 当前 API 路由不可用或超时，使用可连通 GLM 替代。 |
| `grok-3-mini`、`grok-4.2` | 不跑 | 当前 API 路由不可用或超时，使用可连通 Grok 替代。 |

## 运行命令

全量扩展评测使用 `evaluator/run_full_panel.py`。该脚本会对每个模型循环执行 04 和 05，直到该模型达到完整可统计状态。

```bash
python3 evaluator/run_full_panel.py \
  --models gpt-5.2 gpt-5.3-codex gpt-5.3-codex-high claude-sonnet-4-6 claude-opus-4-6 gemini-3-flash-preview-thinking qwen2.5-14b-instruct qwen3.5-397b-a17b deepseek-r1 deepseek-v3.2 deepseek-v3.2-thinking llama3.1-8b llama-3.3-70b llama-4-maverick-17b-128e-instruct glm-4-32b-0414 glm-4.5-air glm-4.7 glm-5 grok-3 grok-3-reasoner grok-3-reasoning grok-4 \
  --input dataset/full_all/03c_selected_records.jsonl \
  --inference-dir dataset/full_all/04_inference_expanded \
  --judged-dir dataset/full_all/05_judged_expanded \
  --metrics-output dataset/full_all/06_metrics_report_expanded.md \
  --status-output dataset/full_all/expanded_full_eval_status.md \
  --parallel-models 3 \
  --inference-workers 24 \
  --judge-workers 24 \
  --max-rounds 8 \
  --retries 10 \
  --judge-retries 8 \
  --empty-response-retries 12 \
  --incomplete-response-retries 12 \
  --request-timeout 240 \
  --judge-mode llm \
  --judge-model gpt-5.2
```

如果某个慢模型影响整体推进，可以单独指定模型继续跑：

```bash
python3 evaluator/run_full_panel.py \
  --models deepseek-v3.2-thinking qwen3.5-397b-a17b \
  --input dataset/full_all/03c_selected_records.jsonl \
  --inference-dir dataset/full_all/04_inference_expanded \
  --judged-dir dataset/full_all/05_judged_expanded \
  --metrics-output dataset/full_all/06_metrics_report_expanded.md \
  --status-output dataset/full_all/expanded_full_eval_status.md \
  --parallel-models 2 \
  --inference-workers 24 \
  --judge-workers 24 \
  --judge-mode llm \
  --judge-model gpt-5.2
```

## 论文标注

需要在论文表格或脚注中标注以下重叠关系：

- `gpt-4o-mini`、`qwen3-30b-a3b-instruct-2507`、`gemini-3-flash-preview`：03B calibration-overlap。
- `gpt-5.4`、`qwen3-30b-a3b-instruct-2507`：02 generation-overlap。
- `gpt-5.2`：05 judge-overlap，如果作为 target 进入主表，建议后续用另一个 judge 做审计。
- `gemini-2.5-pro`、`claude-sonnet-4-6-thinking`、`deepseek-v3.2-thinking`：03A safety-verifier-overlap。
