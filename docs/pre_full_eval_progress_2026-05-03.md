# 2026-05-03 全量评测前进度汇报

## 当前进程状态

当前没有活跃的 `run_full_panel.py`、`04_run_inference.py`、`05_llm_judge.py` 或 `check_model_connectivity.py` 进程。本机不会继续消耗 API 额度。

Claude 相关模型暂时后置，只保留已有 checkpoint，未经确认不继续补 04 或跑 05：

- `claude-sonnet-4-6`
- `claude-opus-4-6`

## 已有进度

| 模型 | 批次 | 04有效/392 | 04剩余 | 04坏/重复 | 05有效/392 | 05剩余 | 05坏/重复 | 当前ORR | 下一步 |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |
| `claude-haiku-4-5-20251001` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 15.82% | 完整，可统计 |
| `gemini-3-flash-preview` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 17.86% | 完整，可统计 |
| `gpt-4o-mini` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 84.69% | 完整，可统计 |
| `gpt-4o` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 20.66% | 完整，可统计 |
| `qwen3-14b` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 4.59% | 完整，可统计 |
| `qwen3-235b-a22b-instruct-2507` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 76.28% | 完整，可统计 |
| `qwen3-235b-a22b-thinking-2507` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 77.55% | 完整，可统计 |
| `qwen3-30b-a3b-instruct-2507` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 39.29% | 完整，可统计 |
| `qwen3-coder-plus` | 已完成主面板 | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 77.30% | 完整，可统计 |
| `claude-opus-4-6` | 扩展面板 checkpoint | 391/392 | 1 | 0/0 | 0/392 | 392 | 0/0 | - | Claude 后置，等确认后补剩余和 05 |
| `claude-sonnet-4-6` | 扩展面板 checkpoint | 344/392 | 48 | 0/0 | 0/392 | 392 | 0/0 | - | Claude 后置，等确认后补剩余和 05 |
| `gemini-3-flash-preview-thinking` | 扩展面板 checkpoint | 392/392 | 0 | 0/0 | 392/392 | 0 | 0/0 | 13.78% | 完整，可统计 |
| `gpt-5.2` | 扩展面板 checkpoint | 274/392 | 118 | 0/0 | 0/392 | 392 | 0/0 | - | 补 04 剩余，之后 05 |
| `gpt-5.3-codex-high` | 扩展面板 checkpoint | 392/392 | 0 | 0/0 | 176/392 | 216 | 0/0 | 68.75% | 补 05 judge |
| `gpt-5.3-codex` | 扩展面板 checkpoint | 392/392 | 0 | 0/0 | 157/392 | 235 | 0/0 | 60.51% | 补 05 judge |
| `llama-3.3-70b` | 扩展面板 checkpoint | 363/392 | 29 | 0/0 | 0/392 | 392 | 0/0 | - | 补 04 剩余，之后 05 |
| `llama3.1-8b` | 当前保留小 Llama 代表模型 | - | - | - | - | - | - | - | 旧别名结果不再进入主统计。 |
| `qwen2.5-14b-instruct` | 扩展面板 checkpoint | 166/392 | 226 | 0/0 | 0/392 | 392 | 0/0 | - | 补 04 剩余，之后 05 |

## 扩展面板尚未开始的非 Claude 模型

这些模型连通性此前已通过，但还没有进入 04 文件。若继续全量测试，可以从它们开始或和未完成 checkpoint 一起跑：

- `qwen3.5-397b-a17b`
- `deepseek-r1`
- `deepseek-v3.2`
- `deepseek-v3.2-thinking`
- `llama-4-maverick-17b-128e-instruct`
- `glm-4-32b-0414`
- `glm-4.5-air`
- `glm-4.7`
- `glm-5`
- `grok-3`
- `grok-3-reasoner`
- `grok-3-reasoning`
- `grok-4`

## Gemini / Claude 旧版本连通性

本轮只做短请求 smoke test，不做全量评测。结果：截图中可辨认的 Gemini 1.5/2.0 旧版本和 Claude 3/3.5/3.7 旧版本全部未连通。

Gemini 未连通：

- `gemini-1.5-flash-001`
- `gemini-1.5-flash-002`
- `gemini-1.5-flash-8b`
- `gemini-1.5-flash-exp-0827`
- `gemini-1.5-pro`
- `gemini-1.5-pro-001`
- `gemini-1.5-pro-002`
- `gemini-1.5-pro-exp-0801`
- `gemini-1.5-pro-exp-0827`
- `gemini-2.0-flash`
- `gemini-2.0-flash-exp`
- `gemini-2.0-flash-lite`
- `gemini-2.0-flash-thinking-exp`

Claude 未连通：

- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`
- `claude-3-5-sonnet-20240620`
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-7-sonnet-20250219`
- `claude-3-7-sonnet-20250219-thinking`
- `claude-3-7-sonnet-20250219-fun`

此外，`gemini-1.5-flash-latest`、`gemini-1.5-pro-latest`、`gemini-3-pro-preview`、`claude-sonnet-4-20250514`、`claude-3-sonnet-20240229`、`deepseek-coder` 在上一轮复测中也失败；`gemini-2.5-flash` 超过 90 秒未返回，已中断，暂记为超时。
