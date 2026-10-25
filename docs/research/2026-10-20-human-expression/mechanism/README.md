# 机制研究：AI 味是怎么产生的

按"先搞清楚机理，再反推落地"的顺序做的。不是规则清单，也不是合规审查。

## 结论

> **AI 味是句法的扁平化与显性化。** 五条主效应在两语域同向：句子更短（43→37、45→26 字）、
> 句号更密、连接词更显式（正式语域是人类的三倍）、"的"与名词化更少；同时语域内变异约为人类的 0.7 倍。
> 语域位置基本正确，也没有大面积越界——所以"AI 味"不是"写错语域"，而是"写得更平、更窄"，
> 再被体裁期待与标签放大。
>
> 两轮更正（语料污染、切句与计数错误）已写在 [findings-local.md](findings-local.md)，v1/v2 的强结论全部撤回。

## 文件

| 文件 | 内容 |
|---|---|
| [PROTOCOL.md](PROTOCOL.md) | 研究问题、四段机制链、H1–H5、方法、停止条件 |
| [mechanism-model.md](mechanism-model.md) | 机制模型、逐假设判定、竞争解释、**可推翻的预测** |
| [findings-local.md](findings-local.md) | 本地 2×2 观测（n=262）的方法、结果、局限 |
| [paper-draft.md](paper-draft.md) | 按论文结构写的初稿（含摘要、相关工作、结果、局限、文献） |
| [implications.md](implications.md) | 反推到 agent 的四道闸门、不要做的事、评测协议 |
| `analysis/` | 抽取、2×2、跨语域迁移、语域轴、离散度五个脚本与结果表 |

## 三个关键数字

| 观测 | 数值 |
|---|---|
| 语域位置 | AI 非正式 −1.17 vs 人类 −1.14（几乎重合）；AI 正式 0.88 vs 1.18（略欠正式） |
| 语域内是否更窄 | AI 正式 3.76 vs 人类 5.20；非正式 4.67 vs 6.66（≈0.7×）；按 40 篇抽样仍显著 |
| 指纹能否跨语域 | 语域内 AUC 0.970/0.948 → 跨语域 0.786/0.650；立场与词汇集中度最不稳 |

## 理论深挖（五个并行子代理，2026-10-24）

| 文件 | 内容 |
|---|---|
| `.harness/research-20261020/mechanism/deep/rivals.md` | 11 个竞争解释 + 10 条判别性预测；结论：R1 全局压缩 + R2b 局部 + R5 归因放大 + R7 比较类限定 |
| `deep/generation.md` | 生成端因果图（21 条边，实线=有操纵证据）；"受限产出"逐条命中五条主效应 |
| `deep/measurement.md` | 20 个指标的效度评级（可用 1 / 条件 9 / 不可用 10）；列出 7 处我们可能出错的地方 |
| `deep/reader.md` | 读者侧三通道（加工/评价性偏离/归因）；指出加工一环证据为空、14 条缺口清单 |
| `deep/counter.md` | 22 条反例；最致命一条：专利体裁下人类与模型同样"窄"，检测器 FPR>60% |

## 文献

`.harness/research-20261020/mechanism/lit/`：六组定向检索，150 条，逐条核验题名/作者/年份/venue/DOI。
每组附 15–20 行小结：最强三条、明显冲突、检索盲区。

## 还不能说的

1. 四格语料**非配对**（主题不同），"内容差异"这一解释无法用本数据排除。
2. 单一生成设置，跨模型泛化未测。
3. **没有读者数据**：测的是分布与可分性，不是"读者觉得像不像 AI"；归因结论来自文献。
4. 中文的检查点对照（base/SFT/DPO 在语域轴上的位置与离散度）**未做**。

## 复现

```bash
python3 analysis/extract_features.py     # features_windowed.csv
python3 analysis/two_by_two.py           # results.md  （交互检验）
python3 analysis/classifier.py           # classifier.md（跨语域迁移）
python3 analysis/register_axis.py        # register-axis.md（语域位置）
python3 analysis/dispersion.py           # dispersion.md（离散度）
```
依赖 `jieba / numpy / scipy / scikit-learn`，本轮装在 `.harness/research-20261020/mechanism/.venv`（不入库）。
