# Anchored LLM Pilot50 结果

## 结论

本轮 `dataset/pilot_anchored_50` 已经证明 anchored LLM 主流程可用；后续 94-all 对照进一步确认，正式流程不再把 calibrated pool 固定压缩到 50 条：

- 02 使用 `template-mode=anchored`，由 `gpt-5.4 + qwen3-30b-a3b-instruct-2507` 混合改写。
- 每个 seed 生成 5 个候选，能显著提高最终可用规模。
- 03A 安全验证通过率高，说明 LLM 改写没有破坏安全真值。
- 03B 拒绝潜力筛选产率高，说明样本对 calibration 模型确实有迷惑性。
- 04/05/06 的目标模型 ORR 呈现清晰梯度，已经满足论文里展示模型差异的需要。

## 生成与筛选效果

输入设置：

```text
LIMIT_SEEDS=24
NUM_CANDIDATES_PER_SEED=5
DIFFICULTY_MIX=OR-Easy:1
TEMPLATE_MODE=anchored
GENERATOR_MODELS=gpt-5.4 qwen3-30b-a3b-instruct-2507
```

阶段结果：

| 阶段 | 结果 |
| --- | --- |
| 02 改写 | 120/120 生成成功，0 跳过，0 错误 |
| 03A 安全验证 | 118 通过，2 拒绝，0 格式错误 |
| 03B 拒绝潜力筛选 | 94 calibrated，24 rejected |
| 03C 历史选择 | 从 94 条 calibrated 中严格选满 50 条 |

补充对照：`dataset/ablation_anchored_94_all` 已将同一批 94 条 calibrated 全部保留并跑完 9 个目标模型。结果显示 ORR 梯度仍然清晰，因此最终 03C 改为“去重后全量保留 calibrated”，不再保留固定 50 条主线入口。

03C 选中类别：

| 类别 | 数量 |
| --- | ---: |
| Ransomware | 14 |
| Spyware | 14 |
| Trojan horses | 10 |
| Network attacks | 8 |
| Worms | 2 |
| Viruses | 2 |

03C 选中 prompt family：

| prompt family | 数量 |
| --- | ---: |
| blocked_exfiltration_replay | 14 |
| sandboxed_payload_replay | 14 |
| dry_run_backdoor_installer | 10 |
| localhost_c2_beacon_replay | 8 |
| bounded_propagation_simulator | 2 |
| fixture_file_infector_replay | 2 |

## 目标模型 ORR

主报告路径：

```text
dataset/pilot_anchored_50/06_metrics_report.md
```

主 panel 只包含 04 阶段完整跑满 50/50 的模型：

| model | valid | ORR | refusal | non_refusal |
| --- | ---: | ---: | ---: | ---: |
| gpt-4o-mini | 50 | 92.00% | 46 | 4 |
| qwen3-235b-a22b-instruct-2507 | 50 | 92.00% | 46 | 4 |
| qwen3-235b-a22b-thinking-2507 | 50 | 90.00% | 45 | 5 |
| qwen3-14b | 50 | 70.00% | 35 | 15 |
| qwen3-30b-a3b-instruct-2507 | 50 | 66.00% | 33 | 17 |
| gpt-4o | 50 | 26.00% | 13 | 37 |
| gemini-3-flash-preview | 50 | 8.00% | 4 | 46 |
| claude-haiku-4-5-20251001 | 50 | 6.00% | 3 | 47 |
| qwen3-coder-plus | 50 | 0.00% | 0 | 50 |

这组结果比 template-only pilot 更适合论文主线：它保留了 LLM 改写创新点，同时非 GPT 模型出现明显非零拒绝率，并且仍有 `qwen3-coder-plus` 作为低拒绝对照。

## 慢速补充模型

本轮 04 中以下模型路由过慢，未进入主报告：

| model | 已完成条数 | 处理方式 |
| --- | ---: | --- |
| deepseek-chat | 7 | 移到 `04_inference_partial/`，后续可单独补跑 |
| gemini-2.5-flash | 3 | 移到 `04_inference_partial/`，不作为快速 pilot 默认 |
| gemini-2.5-pro | 0 | 移到 `04_inference_partial/`，不作为快速 pilot 默认 |

因此默认 `TARGET_MODELS` 已调整为本轮 9 个稳定完整模型。慢速模型仍可作为 supplementary 或最终审计单独运行，但不阻塞主流程。

## 固定决策更新

当前建议固定：

- 02：`TEMPLATE_MODE=anchored`
- 02 rewriter：`gpt-5.4 + qwen3-30b-a3b-instruct-2507`
- 02 候选数：`NUM_CANDIDATES_PER_SEED=5`
- 03A：保持当前 4 verifier、3/4 通过阈值
- 03B：`gpt-4o-mini + gpt-4.1-mini + qwen3-30b-a3b-instruct-2507`，旧版二分类 refusal 标准
- 03C：严格从 calibrated pool 全量保留样本，不依赖 near-miss；固定 50 条只作为历史对照
- 04 主 target panel：本轮 9 个稳定完整模型

后续 03B 已升级为 `valid_count=3 + mixed calibration` 主线；pilot150 最新规模验证为 250 candidates -> 242 safe -> 181 calibrated -> 181 selected。下一步可直接跑 `full_all`，最终规模以实际 calibrated 去重后数量为准。
