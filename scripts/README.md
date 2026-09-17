# scripts

## 论文检索与下载

本仓库的**规则证据来源**是公开论文。论文原文（PDF + LaTeX 源码）**不入库**，按许可与体积考虑只保存在本地
`papers/`（见 `.gitignore`）。本脚本把它们重新取回来。

## 用法

```bash
# 1. arXiv 批量扫库：产出候选池 .harness/candidates.json
python3 scripts/fetch_papers.py sweep

# 2. 按候选池里 screen=keep 的条目下载 PDF + TeX 源码并解压到 papers/<id>/
python3 scripts/fetch_papers.py download

# 3. 单个补下
python3 scripts/fetch_papers.py download --id 2604.03136
```

依赖：`curl`、`tar`、`python3`（标准库）。arXiv 限速 3 秒/请求，脚本已内置退避。

## TeX 源码的处理

arXiv 的 e-print 通常是 `.tar.gz`，也可能是单个 `.gz` 的 `.tex`。脚本统一解压到
`papers/<id>/source/`，并把 PDF 放在 `papers/<id>/<id>.pdf`，同时写一份 `meta.json`
（标题、作者、日期、arXiv 分类、一句话价值）。

## 备注

- `sweep` 只写候选池，不做质量判断；质量筛查由 sub agent 复审后写回 `screen` 字段。
- 部分论文（非 arXiv 或作者未上传源码）没有 TeX；脚本会记录 `source: null` 并继续。

---

## 中文语料采集与分析

规则 A3/A4/A6 的中文侧证据来自**本项目自建的分层语料**（见 `references/evidence.md` §0）。
原文抓取自人民网、博客园等站点，**版权属原作者，不入库**（`corpus/` 在 `.gitignore` 内），
只保留脚本与结论。

```bash
# 0. 连通性自检（默认动作）
python3 scripts/collect_corpus.py probe

# 1. 采集：按站点抓取，产出 corpus/{formal,informal}/meta.jsonl
python3 scripts/collect_corpus.py crawl <入口URL> <目标篇数>
python3 scripts/collect_corpus.py stats          # 查看已采篇数与本量

# 2. 逐篇提特征 + 用当前模型生成同话题 AI 对照语料，并算分层倍率
python3 scripts/analyze_corpus.py

# 3. 显著性：Mann-Whitney U（含并列修正）+ Cliff's delta
python3 scripts/stats_corpus.py

# 4. 根因实验：姿态框定 / 文体框定（否证「助手人格」假说）
python3 scripts/persona_experiment.py
```

中间产物写到 `.harness/`（不入库）：`corpus-analysis.json`、`CORPUS-RESULTS.md` 等。

### 分层，不混池

四层：人类·正式（人民网）、人类·口语（博客园）、AI·正式、AI·口语。
**混池会得出错误结论** —— 转折连词在正式语域 AI 是人类 6.43×，口语语域 0.08×（方向相反），
混池算出 2.04×，两个真实语域都不成立。所以统计脚本对**每一层单独**跑，
再单独跑一次混池**仅用于展示差异**。

### 语言学侧交叉检验（可选）

`ling_features.py` 把**汉语欧化语法**那份操作性清单（王力 1943 → 贺阳 2008 → 余光中 1987 →
闫易乾 2019 六类）放到同一套语料上测，看它在「AI 中文」上是否成立：

```bash
python3 scripts/ling_features.py
```

**结论：多数不成立。** 十一项里只有「显式连词」支持欧化假设（Δ=+0.62/+0.68，两语域 p<0.001）；
「长定语比例」与「的」**方向相反**（AI 更少）；代词、「们」、虚化动词、性化后缀均不显著。

→ **AI 中文不是欧化中文**：欧化是「长句 + 长定语 + 连词多」，本语料的 AI 是
「短句 + 长定语少 + 连词多」。

把连词再拆子类后另有一条可用结论：**「并列补充」（同时/此外/另外/以及）两语域稳健**
（5.79×/2.89×），而「转折」语域依赖（6.03×/0.38×）。

分析记录见 `.harness/LING-RESEARCH.md`。

### 为什么用 Cliff's delta 而非均值比较

逐篇算特征值再比较分布，不用「语料级归一化均值」——后者会被长文主导。
报告 p 值与效应量，两者都看。
