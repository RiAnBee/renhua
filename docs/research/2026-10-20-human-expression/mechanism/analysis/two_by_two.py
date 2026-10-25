#!/usr/bin/env python3
"""2x2 analysis: source (human/AI) x register (formal/informal).

For every phenotype feature this reports
  - per-cell medians,
  - source effect within each register (rank-biserial r, Mann-Whitney p),
  - register effect within each source,
  - the interaction F of an aligned-rank-transform ANOVA (does the AI signature
    differ by register? — the operational test of "fixed checklists misfire"),
with Benjamini-Hochberg FDR across features for the interaction test.

Outputs: analysis/results.csv, analysis/results.md
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
SKIP = {"doc", "cell", "source", "register", "chars", "n_sents", "n_paras", "content_tokens", "n_windows"}


def load() -> tuple[list[str], list[dict]]:
    rows = list(csv.DictReader(open(HERE / (sys.argv[1] if len(sys.argv) > 1 else "features_clean.csv"))))
    feats = [k for k in rows[0] if k not in SKIP]
    for r in rows:
        for k in feats:
            r[k] = float(r[k]) if r[k] not in ("", "nan") else float("nan")
    return feats, rows


def rbiserial(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or len(y) < 3:
        return float("nan")
    u = stats.mannwhitneyu(x, y, alternative="two-sided").statistic
    return 2 * u / (len(x) * len(y)) - 1


def mw(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) < 3 or len(y) < 3:
        return float("nan"), float("nan")
    p = stats.mannwhitneyu(x, y, alternative="two-sided").pvalue
    return rbiserial(x, y), p


def art_interaction(rows: list[dict], feat: str) -> tuple[float, float]:
    vals = np.array([r[feat] for r in rows], dtype=float)
    mask = ~np.isnan(vals)
    if mask.sum() < 12:
        return float("nan"), float("nan")
    sub = [r for r, m in zip(rows, mask) if m]
    v = stats.rankdata(vals[mask])
    s = np.array([1.0 if r["source"] == "ai" else 0.0 for r in sub])
    g = np.array([1.0 if r["register"] == "formal" else 0.0 for r in sub])
    X = np.column_stack([np.ones_like(s), s, g, s * g])
    beta, *_ = np.linalg.lstsq(X, v, rcond=None)
    resid = v - X @ beta
    sse_full = resid @ resid
    X0 = X[:, :3]
    beta0, *_ = np.linalg.lstsq(X0, v, rcond=None)
    r0 = v - X0 @ beta0
    sse_red = r0 @ r0
    df2 = len(v) - 4
    if df2 <= 0 or sse_full <= 0:
        return float("nan"), float("nan")
    F = ((sse_red - sse_full) / 1) / (sse_full / df2)
    return F, float(stats.f.sf(F, 1, df2))


def bh(pvals: list[float]) -> list[float]:
    idx = [i for i, p in enumerate(pvals) if not math.isnan(p)]
    ps = sorted((p, i) for i, p in zip(idx, [pvals[i] for i in idx]))
    out = [float("nan")] * len(pvals)
    m = len(ps)
    prev = 1.0
    for rank, (p, i) in enumerate(reversed(ps), start=1):
        q = min(prev, p * m / (m - rank + 1))
        out[i] = q
        prev = q
    return out


def main() -> int:
    feats, rows = load()
    cells = {(s, g): [r for r in rows if r["source"] == s and r["register"] == g]
             for s in ("human", "ai") for g in ("formal", "informal")}
    res = []
    for f in feats:
        def col(k):
            return np.array([r[f] for r in cells[k] if not math.isnan(r[f])])
        hf, hi = col(("human", "formal")), col(("human", "informal"))
        af, ai = col(("ai", "formal")), col(("ai", "informal"))
        if min(len(hf), len(hi), len(af), len(ai)) < 3:
            continue
        r_sf, p_sf = mw(af, hf)      # source effect in formal
        r_si, p_si = mw(ai, hi)      # source effect in informal
        r_rh, p_rh = mw(hi, hf)      # register effect in human
        r_ra, p_ra = mw(ai, af)      # register effect in AI
        F, p_int = art_interaction(rows, f)
        res.append({"feature": f,
                    "med_human_formal": round(float(np.median(hf)), 3),
                    "med_ai_formal": round(float(np.median(af)), 3),
                    "med_human_informal": round(float(np.median(hi)), 3),
                    "med_ai_informal": round(float(np.median(ai)), 3),
                    "r_source_formal": round(r_sf, 3), "p_source_formal": p_sf,
                    "r_source_informal": round(r_si, 3), "p_source_informal": p_si,
                    "r_register_human": round(r_rh, 3), "p_register_human": p_rh,
                    "r_register_ai": round(r_ra, 3), "p_register_ai": p_ra,
                    "F_interaction": round(F, 2), "p_interaction": p_int})
    qs = bh([r["p_interaction"] for r in res])
    for r, q in zip(res, qs):
        r["q_interaction"] = q
    res.sort(key=lambda r: (math.isnan(r["p_interaction"]), r["p_interaction"]))
    with open(HERE / (f"results_{Path(sys.argv[1]).stem}.csv" if len(sys.argv) > 1 else "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)

    sig = [r for r in res if r["q_interaction"] < 0.05]
    md = ["# 2×2 结果（来源 × 语域，n=262）", "",
          f"文档数：人类正式 {len(cells[('human','formal')])}、人类非正式 {len(cells[('human','informal')])}、"
          f"AI 正式 {len(cells[('ai','formal')])}、AI 非正式 {len(cells[('ai','informal')])}。",
          "", "`r` 为秩二列相关（0.1 小 / 0.3 中 / 0.5 大）；`q` 为交互项 BH 校正后的值。", "",
          "## 交互显著的特征（q<0.05）：AI 指纹随语域改变", "",
          "| 特征 | 人类正式 | AI 正式 | 人类非正式 | AI 非正式 | r(正式内) | r(非正式内) | F | q |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in sig:
        md.append(f"| {r['feature']} | {r['med_human_formal']} | {r['med_ai_formal']} | "
                  f"{r['med_human_informal']} | {r['med_ai_informal']} | {r['r_source_formal']} | "
                  f"{r['r_source_informal']} | {r['F_interaction']} | {r['q_interaction']:.3g} |")
    md += ["", "## 全部特征", "", "| 特征 | q(交互) | r 正式内 | r 非正式内 |", "|---|---|---|---|"]
    for r in res:
        q = "nan" if math.isnan(r["q_interaction"]) else f"{r['q_interaction']:.3g}"
        md.append(f"| {r['feature']} | {q} | {r['r_source_formal']} | {r['r_source_informal']} |")
    (HERE / (f"results_{Path(sys.argv[1]).stem}.md" if len(sys.argv) > 1 else "results.md")).write_text("\n".join(md) + "\n")
    print(f"{len(res)} features; {len(sig)} with significant interaction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
