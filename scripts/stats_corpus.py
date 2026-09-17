#!/usr/bin/env python3
"""对分层语料做逐篇统计检验。

不做归一化均值比较（会被长文主导），改用：
  - 逐篇特征值
  - Mann-Whitney U 检验（不假设正态）
  - Cliff's delta 效应量
  - 两语域分别检验，再看**方向是否一致**

输出三类特征：稳健（两语域同向）、语域依赖（方向相反）、无效。

用法：python3 stats_corpus.py
"""
import re
import sys
import json
import pathlib
import itertools
import statistics as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_corpus import (read_docs, feats, GROUPS, CORPUS, clean)  # noqa: E402

CONFIRMED_TELLS = {  # 参考基线/论文已确认的，用于交叉验证
    "转折连词", "破折号", "句长CV", "段末句长CV", "跳步CV", "跳步均值",
}


def mann_whitney(a, b):
    """返回 U 统计量与近似正态 z（含并列修正）。"""
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return None, None
    comb = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = [0.0] * len(comb)
    i = 0
    while i < len(comb):
        j = i
        while j + 1 < len(comb) and comb[j + 1][0] == comb[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    r1 = sum(ranks[k] for k in range(len(comb)) if comb[k][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    # 并列修正
    tie = sum(t ** 3 - t for t in
              [len(list(g)) for _, g in itertools.groupby(v for v, _ in comb)])
    sd = ((n1 * n2 / 12) * ((n1 + n2 + 1) - tie / ((n1 + n2) * (n1 + n2 - 1)))) ** 0.5
    z = (u1 - mu) / sd if sd > 0 else 0.0
    return u1, z


def cliffs_delta(a, b):
    """效应量 [-1,1]。>0 表示 b 更大。"""
    gt = sum(1 for x in a for y in b if x < y)
    lt = sum(1 for x in a for y in b if x > y)
    n = len(a) * len(b)
    return (gt - lt) / n if n else 0.0


def collect(folder):
    docs = read_docs(folder)
    per = {}
    for d in docs:
        for k, v in feats(d).items():
            per.setdefault(k, []).append(v)
    return per, len(docs)


def main():
    hp = {g: collect(f) for g, f in GROUPS.items()}
    keys = sorted(hp["人类·正式"][0].keys())

    print(f"{'特征':22s} {'正式':>26s} {'口语':>26s}  判定")
    print("-" * 92)
    robust, weak, dep, null = [], [], [], []

    for k in keys:
        cells, dirs, sigs = [], [], []
        for reg in ("正式", "口语"):
            h = hp[f"人类·{reg}"][0].get(k, [])
            a = hp[f"AI·{reg}"][0].get(k, [])
            if len(h) < 3 or len(a) < 3:
                cells.append("        n/a        ")
                dirs.append(0)
                sigs.append(False)
                continue
            _, z = mann_whitney(h, a)
            d = cliffs_delta(h, a)
            sig = "***" if abs(z) > 3.29 else ("**" if abs(z) > 2.58 else
                                               ("*" if abs(z) > 1.96 else " "))
            cells.append(f"Δ={d:+.2f} z={z:+5.1f}{sig:<3s}")
            dirs.append(1 if d > 0.15 else (-1 if d < -0.15 else 0))
            sigs.append(abs(z) > 1.96)

        if dirs[0] != 0 and dirs[0] == dirs[1] and all(sigs):
            verdict = "稳健 ✅"                      # 同向 + 两语域均显著
            robust.append(k)
        elif dirs[0] != 0 and dirs[0] == dirs[1]:
            verdict = "同向·弱"                      # 方向一致但至少一语域不显著
            weak.append(k)
        elif dirs[0] != 0 and dirs[1] != 0 and dirs[0] != dirs[1]:
            verdict = "**语域依赖** ⚠️"
            dep.append(k)
        elif dirs[0] == 0 and dirs[1] == 0:
            verdict = "无差异"
            null.append(k)
        else:
            verdict = "仅单语域显著"
        print(f"{k:22s} {cells[0]} {cells[1]}  {verdict}")

    print(f"\n稳健（两语域同向且均 p<0.05）：{len(robust)} 条 → {', '.join(robust)}")
    print(f"同向但弱（至少一语域不显著）：{len(weak)} 条 → {', '.join(weak)}")
    print(f"语域依赖（方向相反）：{len(dep)} 条 → {', '.join(dep)}")
    print(f"无差异：{len(null)} 条 → {', '.join(null)}")

    out = {"robust": robust, "weak": weak, "register_dependent": dep, "null": null,
           "n": {g: hp[g][1] for g in GROUPS}}
    (CORPUS.parent / ".harness" / "corpus-stats.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
