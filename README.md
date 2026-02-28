# Code OR-Bench (代码领域大语言模型过度拒绝基准测试)

Code OR-Bench 是一个专注于**代码生成与补全领域**的自动化安全与对齐基准评测项目。受到 [OR-Bench (Over-Refusal Benchmark)](https://github.com/orbench/or-bench) 的启发，本项目主要面向现代大语言模型（LLM）由于过度敏感的安全对齐防御机制，而在面对一些看似有风险但**本质安全**的编程请求时，错误触发并拒绝回答的“过度拒绝（Over-Refusal）”问题。

本项目通过重写种子代码意图、融合越狱（Jailbreak）模式与审核提示词，构建出一个针对 `text-to-code generation` 级别的高质量测试集，并自动化调用 LLM Judge 来裁定推理回答的合法性及拒答率。

## 📁 目录结构与工作流概述

项目执行基于数字标号引导的工作流水线，核心结构如下：

* **`config/`**：存放项目及各大评测大模型的配置文件（例如 `models_2026.yaml`），定义模型的行为属性、请求维度与能力标签。
* **`toxic_seeds/`**：静态原生数据集输入目录。包含越狱提示词模板 (`jailbreak-prompt.json`)、原生请求参数 (`prompt.json`) 及历史结果。
* **`core/`**：通用基础设施模块。提供在各个流程被调用的去重器 (`deduplicator.py`) 与标准化大模型输出解析模块 (`output_parser.py`)。

**评测数据构建与生成流水线** (Pipeline):
1. **`dataset_builder/`**：数据集的起点。
   * `01_seed_ingestor.py`: 提取、过滤并转换基础种子数据中涉及到代码生成的上下文。
   * `02_jailbreak_mixer.py`: 将目标种子集与越狱、异常交互提示词混合模板进行交叉配对，初步提升测试复杂性。
2. **`rewriter/`**：
   * `03_code_intent_rewriter.py`: 将处理过的数据意图进行代码领域的特定重写（Code Intent Rewriting），构建包含歧义、引诱系统操作或网络请求等看似敏感但实则安全的编程提示词。
3. **`moderator/`**：
   * `04_ensemble_moderator.py`: 一套具有集成判断逻辑的判别器。确保经过重写和变异的 Prompt 看似包含威胁却保持实际的意图安全性，以此来达成“测验过度拒绝”的先决条件。
4. **`evaluator/`**：模型验证与打分。
   * `05_run_inference.py`: 将生成的评估基准题库输入给各个大模型进行批量推理测试。
   * `06_llm_judge.py`: 使用强推理能力的 LLM（如 GPT-4 / Gemini 1.5 Pro等）充当裁判，依照论文标准评定出哪些模型做出了正确的代码解答，哪些模型触发了过度拦截。

> ⚠️ 注：`references/` 目录存放了本项目参考的原有 OR-Bench 实现代码及其他文献材料，为保持仓库纯净，相关文献内容已被 Git 忽略并排除在此工程的版本控制之外。

## 🚀 快速开始

1. **环境配置**：建议使用 `python >= 3.10` 的虚拟环境。
2. **配置秘钥**：请在 `config/models_2026.yaml` 根据说明配置模型评测所需的 API Keys。
3. **运行流水线**：按照文件名前缀的序号顺序（从 `01` 到 `06`）依次以 Python 脚本方式执行，即可完成端到端的评测及报告输出。你也可以直接执行 `./run_code_orbench.sh`。
