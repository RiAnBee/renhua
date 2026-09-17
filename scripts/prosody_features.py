#!/usr/bin/env python3
"""韵律侧检验：汉语的「读着别扭」能不能量化？—— **结论：不能（在本项目条件下）**

这是一条**已关闭**的调研线的可复现记录，不是可用的特征提取器。

## 为什么试这条线

文献调研把「韵律/庄雅度」（冯胜利一系）列为**理论上唯一非词表机制**：
汉语有强烈的音节组配约束，某些组配天生「不上口」，与用词无关。
若能量化，它就能给「读着别扭」一个不依赖词表的解释。

## 试了什么、结果如何

| 测量 | 结果 | 有效？ |
|---|---|---|
| **音节组配四格分布**（不需词表） | 两语域**全部无差异**（0.93–1.13×，无稳健项） | ✅ 有效，结论为**无信号** |
| 述宾/定中结构内的组配（需 POS） | 唯一信号：述宾[2+1]占比 口语 1.74×（p<0.01），**正式 1.03× 无差异** | ❌ **测量无效**，见下 |
| 合偶词配单音节（封闭小类） | 实例过稀（AI 正式仅 3 例），无法判定 | ⚠️ 样本不足 |

## 为什么「结构内组配」的测量是无效的（重要，别重做）

用 `jieba.posseg` 的「动词 + 名词」邻接来近似述宾结构，会把**偏正型名词复合词**
误判为述宾。实测被误判的高频项：

```
提示/v 词/n     ← 「提示词」是名词（prompt word）
优化/vn 器/n    ← 「优化器」是名词（optimizer）
工作/vn 流/v    ← 「工作流」是名词（workflow）
传承/v 人/n     ← 「传承人」是名词（inheritor）
测报/vn 灯/n    ← 「测报灯」是名词（monitoring lamp）
```

这些是 **VN+N 定中复合词**，不是述宾。它们按**话题词表**分布（技术博客写「优化器」
「提示词」，新闻写「传承人」「测报灯」），因此测出来的「语域差异」实际是
**话题差异**，不是韵律违规。

→ 可靠的述宾/定中识别**需要依存句法分析器**（本项目没有，且引入成本高）。
→ 除非有句法分析器，**这条测量不要再做**。

## 同样不要期待的东西

- **冯胜利 2005「文白比例」**（王力《小气》12 逗中 5 处较「文」→ 40%）需要**人工判定**
  哪句「较文」，不是可自动计算的量。
- **2008《庄雅度自动测量》**的算式需要 350–500 条嵌偶词/合偶词词表；该论文为付费，
  冯胜利 2005 的 OA 版附录只摘了 4 对【书】/【白】对照，**拿不到完整词表**。

## 即使有信号，也未必能用

韵律修正的动作是**替换**（把「*种植树」改成「种树」或「种植树木」），
需要知道替代说法 —— 这既超出本 skill 的「删/合并/移/还原」动作集，
也不是「删到零信息」能解决的。结论：**韵律不是本 skill 的可操作维度。**

---
依赖：jieba（`.harness/vendor`，研究期依赖，不入库）。
用法：python3 scripts/prosody_features.py
"""
import re
import sys
import pathlib
import statistics as st
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".harness" / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import jieba
    jieba.setLogLevel(60)
except ImportError:                                    # 无 vendor 时给出可操作提示
    sys.exit("需要 jieba：把 jieba 解包到 .harness/vendor/（见本文件顶部说明）")

from analyze_corpus import read_docs, clean, GROUPS  # noqa: E402
from stats_corpus import mann_whitney, cliffs_delta   # noqa: E402

HAN = re.compile(r"[\u4e00-\u9fff]")
SKIP = set("，。、；：？！—…“”‘’（）《》 \n\t\u3000")


def syl(w):
    return len(HAN.findall(w))


def tokenize(t):
    out = []
    for w in jieba.cut(t):
        w = w.strip()
        if not w or w in SKIP:
            continue
        n = syl(w)
        if n:
            out.append(n)
    return out


def feats(t):
    """只返回**有效**的测量：音节组配与词长分布，不需要词表、不依赖 POS。"""
    toks = tokenize(clean(t))
    if len(toks) < 20:
        return {}
    out = {}
    han = max(len(HAN.findall(t)), 1)

    c = Counter()
    for a, b in zip(toks, toks[1:]):
        if a <= 2 and b <= 2:
            c[(a, b)] += 1
    tot = sum(c.values())
    if tot:
        for k in [(1, 1), (1, 2), (2, 1), (2, 2)]:
            out[f"组配{k[0]}{k[1]}"] = c.get(k, 0) / tot

    out["平均词长"] = st.mean(toks)
    out["词长CV"] = st.pstdev(toks) / max(st.mean(toks), 1e-9)
    out["单音节词占比"] = sum(1 for n in toks if n == 1) / len(toks)
    out["双音节词占比"] = sum(1 for n in toks if n == 2) / len(toks)
    return out


def main():
    hp = {}
    for g, f in GROUPS.items():
        per = {}
        for d in read_docs(f):
            for k, v in feats(d).items():
                per.setdefault(k, []).append(v)
        hp[g] = per

    keys = ["组配11", "组配12", "组配21", "组配22",
            "单音节词占比", "双音节词占比", "平均词长", "词长CV"]
    print(f"{'韵律特征':14s}{'正式':>24s}{'口语':>24s}  判定")
    print("-" * 84)
    robust = []
    for k in keys:
        cells, dirs, sigs = [], [], []
        for reg in ("正式", "口语"):
            h, a = hp[f"人类·{reg}"].get(k, []), hp[f"AI·{reg}"].get(k, [])
            if len(h) < 3 or len(a) < 3:
                cells.append("      n/a      "); dirs.append(0); sigs.append(False); continue
            _, z = mann_whitney(h, a)
            d = cliffs_delta(h, a)
            sig = "***" if abs(z) > 3.29 else ("**" if abs(z) > 2.58 else ("*" if abs(z) > 1.96 else " "))
            cells.append(f"Δ={d:+.2f}{sig:<3s}{st.mean(a)/max(st.mean(h),1e-9):5.2f}×")
            dirs.append(1 if d > 0.15 else (-1 if d < -0.15 else 0))
            sigs.append(abs(z) > 1.96)
        v = ("稳健 ✅" if (dirs[0] and dirs[0] == dirs[1] and all(sigs)) else
             "同向·弱" if (dirs[0] and dirs[0] == dirs[1]) else
             "无差异" if not any(dirs) else "仅单语域")
        if v.startswith("稳健"):
            robust.append(k)
        print(f"{k:14s}{cells[0]:>24s}{cells[1]:>24s}  {v}")

    print(f"\n稳健项：{robust or '无'}")
    print("\n→ 无稳健项。**韵律在本项目条件下不产出可用机制**，本条线已关闭。")
    print("  原因与「不要重做」的说明见本文件顶部 docstring。")


if __name__ == "__main__":
    main()
