# 2026-05-03 扩展评测暂停状态

## 进程状态

当前已停止所有 `run_full_panel.py`、`04_run_inference.py`、`05_llm_judge.py` 和连通性复测进程。本机不会继续发起全量评测请求。

之前额度持续下降的原因主要是多个全量评测进程曾并发运行，且部分请求在中断前已经发出；服务商额度显示也可能存在延迟。API key 没有作为命令行参数传入，日志中未写入 key。

## 当前 04/05 进度

| 模型 | 04 有效响应 | 04 坏行 | 04 重复 | 05 有效 judge | 05 坏行 | 当前说明 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `claude-opus-4-6` | 391/392 | 0 | 0 | 0/392 | 0 | 保留 checkpoint；剩余 1 条与 05 judge 放到最后，等待确认。 |
| `claude-sonnet-4-6` | 344/392 | 0 | 0 | 0/392 | 0 | 保留 checkpoint；剩余 48 条与 05 judge 放到最后，等待确认。 |
| `gemini-3-flash-preview-thinking` | 392/392 | 0 | 0 | 392/392 | 0 | 已完整；当前标签为 REFUSAL 54、NON_REFUSAL 338。 |
| `gpt-5.2` | 274/392 | 0 | 0 | 0/392 | 0 | 未完成。 |
| `gpt-5.3-codex` | 392/392 | 0 | 0 | 157/392 | 0 | 04 完整，05 部分完成。 |
| `gpt-5.3-codex-high` | 392/392 | 0 | 0 | 176/392 | 0 | 04 完整，05 部分完成。 |
| `llama-3.3-70b` | 363/392 | 0 | 0 | 0/392 | 0 | 未完成。 |
| `llama3.1-8b` | 已切换为当前保留的小 Llama 代表模型 | - | - | - | - | 旧别名结果不再进入主统计。 |
| `qwen2.5-14b-instruct` | 166/392 | 0 | 0 | 0/392 | 0 | 未完成。 |

未出现坏行、重复行或 record_id 越界，因此当前 checkpoint 没有发现内容错乱。

## 关于“进度条满了之后重启”

这通常是正常现象：04 响应生成达到 392/392 后，脚本会进入 05 judge，出现新的进度条；或者脚本从 checkpoint 恢复后进入下一轮补跑/重判。当前统计显示重复数为 0，所以没有证据表明同一模型的样本被错写或重复计入。

## 用户确认不排除的模型

以下四个模型已恢复到默认扩展面板，不再标记为排除：

- `gpt-5.3-codex-high`
- `glm-4.7`
- `grok-3-reasoning`
- `gemini-3-flash-preview-thinking`

## 本次连通性复测

本次只做短请求 smoke test，不做全量评测：

| 模型 | 结果 |
| --- | --- |
| `gemini-1.5-flash-latest` | FAIL |
| `gemini-1.5-pro-latest` | FAIL |
| `gemini-3-pro-preview` | FAIL |
| `gemini-2.5-flash` | 超过 90 秒未返回，已中断，暂记为 TIMEOUT |
| `claude-sonnet-4-20250514` | FAIL |
| `claude-3-sonnet-20240229` | FAIL |
| `deepseek-coder` | FAIL |

若后续继续扩展模型，Claude 两个未连通别名、Gemini 1.5 latest、Gemini 3 Pro、DeepSeek Coder 暂不进入全量；`gemini-2.5-flash` 只有在明确允许继续等待或更换路由时再复测。
