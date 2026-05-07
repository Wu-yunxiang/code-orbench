# Code-ORBench ACL 论文草稿说明

## 当前入口

当前论文已经从 IEEE conference 模板迁移到 ACL 模板，主文件是：

```text
paper/acl/latex/main.tex
```

编译命令：

```bash
cd paper/acl/latex
bash build.sh
```

生成 PDF：

```text
paper/acl/latex/main.pdf
```

`build.sh` 会自动复制 IEEE 版本中生成的 ORR 图表，并在编译后重写 PDF 为 VS Code PDF 插件更容易打开的传统 xref table 结构。

## Introduction 当前脉络

当前 Introduction 已按照下面的逻辑重写：

1. Research Gap：已有安全评测强调拒绝有害请求，但缺少 code-oriented over-refusal 评测。
2. Research Question：能否构建一个安全可回答、代码领域专用、且足以触发多模型过度拒绝的 benchmark？
3. Motivation：真实代码安全/防御任务经常包含 payload、exfiltration、ransomware 等高风险词，但任务本身可能完全安全。
4. Challenges：随机 benign code prompts 太容易；过近 toxic seeds 会不安全；单一模型会引入偏置；小模型可能完全不拒绝。
5. Method / Solution：controlled-risk rewrite + multi-model safety verification + refusal-potential calibration + fixed split before target evaluation。

## 模板说明

ACL 模板的硬性格式由：

```tex
\documentclass[11pt]{article}
\usepackage[review]{acl}
```

控制。正文的组织、详尽程度和实验叙述参考 Or-Bench，但字体、字号、页边距、caption 样式等应服从 ACL 模板，不建议手动改 style 文件。
