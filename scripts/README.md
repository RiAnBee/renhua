# 论文检索与下载

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
