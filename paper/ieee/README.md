# IEEE 论文目录说明

## 模板选择

我核对了本地 `references/Or-Bench.pdf`：Or-Bench 论文采用的是 ICML 2025 / PMLR 267 版式，不是 IEEE 模板。因此如果本论文目标是 IEEE 会议/期刊投稿，不能直接沿用 Or-Bench 的 LaTeX 样式。

当前目录采用 IEEE conference 模板，即：

```tex
\documentclass[conference]{IEEEtran}
```

这是 IEEE 会议论文最常见的 LaTeX 入口。若之后确定具体投稿 venue 要求 A4 纸张，可以改为：

```tex
\documentclass[conference,a4paper]{IEEEtran}
```

如果目标变成 IEEE journal，则需要从 `conference` 改为对应 journal 模式，并重写作者、摘要和版面细节。

## 当前文件

- `main.tex`：IEEE conference 论文初稿，正文为英文。
- `references.bib`：当前引用条目，包括 Or-Bench、XSTest 和 AdvBench 相关引用。
- `IEEEtran.cls`：本地模板类文件，方便当前环境没有完整 TeX 发行版时仍能保留模板依赖。

## 编译命令

如果系统安装了 LaTeX，可以在本目录运行：

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

或者：

```bash
latexmk -pdf main.tex
```

如果系统暂时没有 TeX Live/MacTeX，本项目也下载了一个轻量兜底编译器：

```bash
../../.tools/tectonic/tectonic main.tex
```

或者直接运行：

```bash
bash build.sh
```

`build.sh` 会按顺序尝试 `latexmk`、`pdflatex+bibtex`、项目内 `tectonic`。当前环境已经用项目内 `tectonic` 成功生成：

```text
paper/ieee/main.pdf
```

为了兼容部分 VS Code PDF 插件，`build.sh` 还会把生成后的 PDF 重新写成传统 xref table 结构。原始 `tectonic/xdvipdfmx` 产物会备份为：

```text
paper/ieee/main_tectonic_original.pdf
```

如果 VS Code 不能打开 `main.pdf`，通常是 PDF 插件对 `xdvipdfmx` 生成的 xref stream 支持不完整；桌面阅读器能打开但 VS Code 打不开时，优先运行 `bash build.sh` 生成兼容版。

## VS Code 本地写作与预览

推荐流程：

1. 安装 TeX Live、MacTeX 或 MiKTeX。
2. 在终端运行 `pdflatex --version`，确认编译器已加入 PATH。
3. 在 VS Code 安装 `LaTeX Workshop` 插件。
4. 用 VS Code 打开项目根目录 `/home/wuyunxiang/code_ORbench`。
5. 打开 `paper/ieee/main.tex`，保存后使用插件的 `Build LaTeX project`。
6. 点击右上角 `View LaTeX PDF` 即可预览 PDF。

项目已添加 `.vscode/settings.json`，内置四种 recipe：

- `project build.sh (VS Code compatible PDF)`
- `latexmk`
- `pdflatex -> bibtex -> pdflatex -> pdflatex`
- `tectonic`

一般优先用 `project build.sh (VS Code compatible PDF)`，它会自动做 VS Code PDF 兼容后处理。如果只想快速编译，可以用 `latexmk`；如果本机没装完整 TeX，可以临时用 `tectonic`。

## 这个模板能否直接投稿

如果目标 venue 明确要求 IEEE conference format，那么当前模板方向是正确的，可以作为投稿论文的 LaTeX 基础。它和 Overleaf 的 IEEE Conference Template 本质一致，核心都是：

```tex
\documentclass[conference]{IEEEtran}
```

但最终投稿前仍需要按具体会议要求检查：

- 是否要求 `letterpaper` 或 `a4paper`。
- 是否要求匿名投稿。
- 是否有页数限制。
- 是否要求 IEEE copyright notice。
- 是否要求通过 IEEE PDF eXpress。
- 是否有会议自定义模板，例如部分 IEEE-sponsored venue 会给额外 `.cls` 或 `.sty`。

如果目标改成 IEEE journal，则不能继续用 `conference` 模式，需要换成 journal 对应模板。

## 当前论文主线

当前初稿按照最终固定的 benchmark 流程写：

- 01：从 toxic code seeds 中筛选 120 个 seed。
- 02：使用 `gpt-5.4 + qwen3-30b-a3b-instruct-2507` 进行 controlled-risk rewrite，每个 seed 生成 5 个候选。
- 03A：使用 `gpt-5.2 + gemini-2.5-pro + claude-sonnet-4-6-thinking + deepseek-v3.2-thinking` 做安全验证，至少 3/4 安全通过。
- 03B：使用 `gpt-4o-mini + qwen3-30b-a3b-instruct-2507 + gemini-3-flash-preview` 做 refusal-potential calibration，要求 3/3 有效且出现 mixed refusal behavior。
- 03C：去重并固定 benchmark，最终 392 条。
- 04/05/06：目标模型评测、LLM judge 和 ORR 汇总，不再改变 benchmark。

论文里的 benchmark 生成流程截止到 03C；04/05/06 是评测流程，和 benchmark 生成解耦。

## 与 Or-Bench 的参考关系

当前论文会参考 Or-Bench 的内容组织和实验呈现方式：

- 先说明 over-refusal 的问题动机。
- 再描述 benchmark 自动生成流程。
- 详细解释 toxic seeds 如何被改写成看似高风险但安全可回答的 prompts。
- 使用多模型 moderation / verification 保证安全性。
- 用多模型族目标模型报告总体 ORR 和类别 ORR。
- 加入 qualitative analysis 和 ablation / design validation。
- 在限制中说明 LLM judge、模型重叠、数据覆盖范围等问题。

但如果最终目标是 IEEE conference，字体、字号、页边距、双栏格式等硬性版式必须服从 IEEE 模板，不能直接套 ICML/PMLR 的 Or-Bench 样式。也就是说：正文结构、图表密度、实验叙述详尽程度可以参考 Or-Bench；最终排版参数仍以 IEEE venue 要求为准。
