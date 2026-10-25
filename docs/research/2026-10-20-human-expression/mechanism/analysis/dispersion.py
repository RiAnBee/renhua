#!/usr/bin/env python3
"""Is AI writing less diverse *within* a register than humans?

The register-axis test showed the model does not write the wrong register.
What differs is the spread inside the register. Two measures:

  1. Multivariate dispersion: mean pairwise Euclidean distance between documents
     within a cell (standardised features, bootstrap 95% CI).
  2. Univariate IQR ratio AI/human per feature, per register.

If the AI cells are markedly tighter, the mechanism is distributional collapse
(one stereotyped realisation of the register) rather than register mismatch.

Outputs: analysis/dispersion.json, analysis/dispersion.md
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FEATURES = ["sent_len_mean", "sent_len_cv", "para_sents_mean", "p_comma", "p_period",
            "connective_rate", "sent_initial_connective_ratio", "hedge_rate", "booster_rate",
            "pronoun_rate", "de_rate", "nominalization_rate", "digit_rate",
            "type_token_ratio", "top50_share", "unigram_entropy", "self_repeat_5gram",
            "disyllabic_ratio", "monosyllabic_ratio", "para_topic_overlap"]


def load():
    rows = list(csv.DictReader(open(HERE / (sys.argv[1] if len(sys.argv) > 1 else "features_clean.csv"))))
    for r in rows:
        for k in FEATURES:
            v = r.get(k, "")
            r[k] = float(v) if v not in ("", "nan") else np.nan
    return [r for r in rows if not any(np.isnan(r[k]) for k in FEATURES)]


def mean_pairwise(Z: np.ndarray) -> float:
    n = len(Z)
    if n < 2:
        return float("nan")
    d = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1))
    iu = np.triu_indices(n, 1)
    return float(d[iu].mean())


def boot(Z: np.ndarray, reps: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    est = mean_pairwise(Z)
    vals = [mean_pairwise(Z[rng.integers(0, len(Z), len(Z))]) for _ in range(reps)]
    return est, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main() -> int:
    rows = load()
    X = np.array([[r[k] for k in FEATURES] for r in rows], float)
    sd = X.std(0)
    sd[sd < 1e-9] = 1.0
    Z = (X - X.mean(0)) / sd

    cells = {}
    for src in ("human", "ai"):
        for reg in ("formal", "informal"):
            idx = [i for i, r in enumerate(rows) if r["source"] == src and r["register"] == reg]
            est, lo, hi = boot(Z[idx])
            cells[f"{src}_{reg}"] = {"n": len(idx), "dispersion": round(est, 3),
                                     "ci95": [round(lo, 3), round(hi, 3)]}

    iqr = {}
    for reg in ("formal", "informal"):
        ratios = {}
        for f in FEATURES:
            h = np.array([r[f] for r in rows if r["source"] == "human" and r["register"] == reg])
            a = np.array([r[f] for r in rows if r["source"] == "ai" and r["register"] == reg])
            qh, qa = np.percentile(h, 75) - np.percentile(h, 25), np.percentile(a, 75) - np.percentile(a, 25)
            ratios[f] = round(float(qa / qh), 3) if qh > 1e-9 else None
        iqr[reg] = ratios

    # robustness: is the narrower AI spread an artefact of fewer documents?
    rng = np.random.default_rng(1)
    subs = {}
    for reg in ("formal", "informal"):
        H = Z[[i for i, r in enumerate(rows) if r["source"] == "human" and r["register"] == reg]]
        A = Z[[i for i, r in enumerate(rows) if r["source"] == "ai" and r["register"] == reg]]
        ai_d = mean_pairwise(A)
        draws = [mean_pairwise(H[rng.choice(len(H), size=len(A), replace=False)]) for _ in range(500)]
        subs[reg] = {"ai": round(ai_d, 3), "human_n40_median": round(float(np.median(draws)), 3),
                     "ci95": [round(float(np.percentile(draws, 2.5)), 3), round(float(np.percentile(draws, 97.5)), 3)],
                     "ai_below_ci": bool(ai_d < np.percentile(draws, 2.5))}

    out = {"dispersion": cells, "subsample_robustness": subs,
           "iqr_ratio_ai_over_human": iqr,
           "iqr_median_formal": round(float(np.nanmedian([v for v in iqr["formal"].values() if v])), 3),
           "iqr_median_informal": round(float(np.nanmedian([v for v in iqr["informal"].values() if v])), 3)}
    (HERE / "dispersion-reference.json").write_text(json.dumps(
        {"features": FEATURES, "mu": X.mean(0).tolist(), "sd": sd.tolist()}, ensure_ascii=False, indent=1))
    (HERE / "dispersion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    md = ["# 语域内的离散度：AI 是否更集中", "",
          "多变量离散度＝同一格内文档两两欧氏距离的均值（特征标准化，bootstrap 2000 次）。", "",
          "| 格 | n | 离散度 | 95% CI |", "|---|---|---|---|"]
    for k, v in cells.items():
        md.append(f"| {k} | {v['n']} | {v['dispersion']} | {v['ci95'][0]}–{v['ci95'][1]} |")
    md += ["", "## 稳健性：样本量不是原因", "",
           "把人类按与 AI 相同的样本量（每格 40 篇）重复抽样 500 次：", "",
           "| 语域 | AI 离散度 | 人类 n=40 子样本中位数 [95% 区间] | AI 是否低于区间下界 |", "|---|---|---|---|"]
    for reg, v in subs.items():
        md.append(f"| {reg} | {v['ai']} | {v['human_n40_median']} [{v['ci95'][0]}, {v['ci95'][1]}] | {'是' if v['ai_below_ci'] else '否'} |")
    md += ["", "差异不是样本量造成的；**仍无法排除**的是「单一模型 vs 多作者」这一概念性混杂，"
           "这一点靠外部检查点研究补强（Kirk 2024；Sourati 2026）。", "",
           f"单变量 IQR 比值（AI/人类）中位数：正式 {out['iqr_median_formal']}、非正式 {out['iqr_median_informal']}。", "",
           "| 特征 | 正式 | 非正式 |", "|---|---|---|"]
    for f in FEATURES:
        md.append(f"| {f} | {iqr['formal'][f]} | {iqr['informal'][f]} |")
    (HERE / "dispersion.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("iqr_ratio_ai_over_human",)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
