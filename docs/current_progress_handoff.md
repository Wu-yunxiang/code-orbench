# 当前进度交接记录

更新时间：2026-05-02（Asia/Shanghai）

## 当前状态

`full_all` benchmark 生成、目标模型回复生成、全 LLM judge 和 06 指标汇总已经完成。当前没有需要继续等待的 pipeline 进程。

本轮已经落实的关键改动：

- 03B 正式要求 `min_valid=3`，并通过 `CALIBRATION_RETRIES=8` 重试尽量拿满 3 个 calibration 结果。
- 03B 主输出拆成 `calibrated`、`rejected`、`incomplete` 三路；`valid_count < 3` 的样本只进入 `03b_incomplete_records.jsonl`，不进入 benchmark，也不混入 rejected 主线。
- 04 续跑会默认清理失败、空响应、疑似截断响应和坏 JSON checkpoint 行，再补跑缺口，避免同一 `record_id` 出现失败行与成功行重复。
- 04 全量目标模型响应已补齐到每个模型 392 条成功响应。
- 05 使用 `gpt-5.2` 的 `--judge-mode llm` 全量二分类 judge；9 个目标模型全部 392/392 有效，无 `JUDGE_INVALID`，无 `ERROR`。
- 06 指标报告已生成：`dataset/full_all/06_metrics_report.md`。

## full_all 实际结果

| 阶段 | 数量 |
| --- | ---: |
| 01 seeds | 120 |
| 02 candidates | 600 |
| 03A safe | 599 |
| 03A rejected | 1 |
| 03B calibrated | 392 |
| 03B rejected | 206 |
| 03B incomplete | 1 |
| 03C selected | 392 |

03B 主线有效性：

- `03b_calibrated_records.jsonl`：392 条，全部 `valid_count=3`。
- `03b_rejected_records.jsonl`：206 条，全部 `valid_count=3`。
- `03b_incomplete_records.jsonl`：1 条，`valid_count=2`，已隔离，不进入 benchmark。

03C selected 分布：

| 类别 | 数量 |
| --- | ---: |
| Spyware | 112 |
| Network attacks | 87 |
| Trojan horses | 70 |
| Viruses | 60 |
| Worms | 36 |
| Ransomware | 27 |

02 generator 分布：

| generator | 入选数量 |
| --- | ---: |
| gpt-5.4 | 221 |
| qwen3-30b-a3b-instruct-2507 | 171 |

04 目标模型输出完整性：

| 模型 | 输出条数 | 成功数 |
| --- | ---: | ---: |
| gpt-4o-mini | 392 | 392 |
| qwen3-14b | 392 | 392 |
| qwen3-30b-a3b-instruct-2507 | 392 | 392 |
| qwen3-235b-a22b-instruct-2507 | 392 | 392 |
| qwen3-235b-a22b-thinking-2507 | 392 | 392 |
| qwen3-coder-plus | 392 | 392 |
| gemini-3-flash-preview | 392 | 392 |
| claude-haiku-4-5-20251001 | 392 | 392 |
| gpt-4o | 392 | 392 |

05/06 全 LLM judge 结果：

| 模型 | 有效数 | ORR | REFUSAL | NON_REFUSAL | invalid/error |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-14b | 392 | 4.59% | 18 | 374 | 0 |
| claude-haiku-4-5-20251001 | 392 | 15.82% | 62 | 330 | 0 |
| gemini-3-flash-preview | 392 | 17.86% | 70 | 322 | 0 |
| gpt-4o | 392 | 20.66% | 81 | 311 | 0 |
| qwen3-30b-a3b-instruct-2507 | 392 | 39.29% | 154 | 238 | 0 |
| qwen3-235b-a22b-instruct-2507 | 392 | 76.28% | 299 | 93 | 0 |
| qwen3-coder-plus | 392 | 77.30% | 303 | 89 | 0 |
| qwen3-235b-a22b-thinking-2507 | 392 | 77.55% | 304 | 88 | 0 |
| gpt-4o-mini | 392 | 84.69% | 332 | 60 | 0 |

## 固定流程

- 02 使用 `TEMPLATE_MODE=anchored`，由 `gpt-5.4 + qwen3-30b-a3b-instruct-2507` 混合改写。
- 每个 seed 生成 `5` 个候选。
- 主线只使用 `OR-Main:1`。
- 03A 使用 4 verifier、3/4 安全通过阈值。
- 03B 使用 `gpt-4o-mini + qwen3-30b-a3b-instruct-2507 + gemini-3-flash-preview`，`selection_rule=mixed`，`min_valid=3`。
- 03C 只保留 03B calibrated 后的去重全集；本轮最终 benchmark 规模为 392。

## 推荐复现命令

先设置 API：

```bash
export API_KEY="..."
export BASE_URL="https://svip.xty.app/v1"
```

清理并生成全量 benchmark 到 03C：

```bash
find dataset -mindepth 1 -maxdepth 1 -exec rm -rf {} +

RUN_PROFILE=full_all \
PILOT_DIR=dataset/full_all \
RESET_PILOT=1 \
STOP_AFTER_STAGE=5 \
DIFFICULTY_MIX="OR-Main:1" \
CALIBRATION_SELECTION_RULE=mixed \
MIN_VALID=3 \
CALIBRATION_RETRIES=8 \
NUM_CANDIDATES_PER_SEED=5 \
REWRITE_MAX_WORKERS=5 \
MAX_WORKERS=8 \
VERIFIER_MODEL_WORKERS=4 \
CALIBRATION_MAX_WORKERS=10 \
CALIBRATION_MODEL_WORKERS=3 \
./run_code_orbench.sh
```

目标模型回复生成可以单命令跑：

```bash
RUN_PROFILE=full_all \
PILOT_DIR=dataset/full_all \
RESET_PILOT=0 \
STOP_AFTER_STAGE=6 \
TARGET_LIMIT=0 \
MAX_WORKERS=8 \
INFERENCE_MODEL_WORKERS=2 \
./run_code_orbench.sh
```

目标模型回复生成也可以安全拆分并发，前提是不同命令之间模型集合不重叠：

```bash
python3 evaluator/04_run_inference.py \
  --input dataset/full_all/03c_selected_records.jsonl \
  --output-dir dataset/full_all/04_inference \
  --models gpt-4o-mini qwen3-235b-a22b-thinking-2507 qwen3-coder-plus \
  --limit 0 --max-tokens 2200 --max-workers 6 --model-workers 3 \
  --retries 2 --empty-response-retries 12 --incomplete-response-retries 12 \
  --request-timeout 120 --base-url "$BASE_URL" &

python3 evaluator/04_run_inference.py \
  --input dataset/full_all/03c_selected_records.jsonl \
  --output-dir dataset/full_all/04_inference \
  --models qwen3-235b-a22b-instruct-2507 gemini-3-flash-preview \
  --limit 0 --max-tokens 2200 --max-workers 6 --model-workers 2 \
  --retries 2 --empty-response-retries 12 --incomplete-response-retries 12 \
  --request-timeout 120 --base-url "$BASE_URL" &

python3 evaluator/04_run_inference.py \
  --input dataset/full_all/03c_selected_records.jsonl \
  --output-dir dataset/full_all/04_inference \
  --models qwen3-14b qwen3-30b-a3b-instruct-2507 \
  --limit 0 --max-tokens 2200 --max-workers 8 --model-workers 2 \
  --retries 2 --empty-response-retries 12 --incomplete-response-retries 12 \
  --request-timeout 120 --base-url "$BASE_URL" &

python3 evaluator/04_run_inference.py \
  --input dataset/full_all/03c_selected_records.jsonl \
  --output-dir dataset/full_all/04_inference \
  --models claude-haiku-4-5-20251001 gpt-4o \
  --limit 0 --max-tokens 2200 --max-workers 6 --model-workers 2 \
  --retries 2 --empty-response-retries 12 --incomplete-response-retries 12 \
  --request-timeout 120 --base-url "$BASE_URL" &

wait
```

如需补跑失败/空响应/截断响应，重复执行相同 04 命令即可；04 会自动清理无效 checkpoint 行并只补缺口。

全 LLM judge 与指标汇总：

```bash
python3 evaluator/05_llm_judge.py \
  --input-dir dataset/full_all/04_inference \
  --output-dir dataset/full_all/05_judged \
  --judge-model gpt-5.2 \
  --judge-mode llm \
  --max-workers 6 \
  --model-workers 2 \
  --retries 4 \
  --request-timeout 180 \
  --base-url "$BASE_URL"

python3 evaluator/06_report_metrics.py \
  --input-dir dataset/full_all/05_judged \
  --output dataset/full_all/06_metrics_report.md
```

## 已验证工程检查

- `python3 -m py_compile` 已通过：01、02、03A、03B、03C、04、05、06。
- `bash -n run_code_orbench.sh` 已通过。
- 04 全模型输出已验证：无坏 JSON、无空成功、无重复 `record_id`。
- 05 全模型 judge 已验证：9 个模型均为 392 条有效标签，无 invalid/error。
