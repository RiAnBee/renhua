#!/usr/bin/env python3
"""Where does AI informal prose sit on the human formal-informal axis?

H2 (register collapse) predicts that AI informal text should drift toward the
formal pole defined by human writing, not toward the informal pole it was asked
to write in. A register axis is estimated only from HUMAN documents:

    w = mean(human_formal) - mean(human_informal)      (standardised features)

then every document is projected onto w. If the AI-informal median sits closer to
human-formal than to human-informal, the model is writing the wrong register.

Also reports the share of documents that fall on the "wrong side" of the human
midpoint — a direct measure of how often each cell misses its own register.

Outputs: analysis/register-axis.json, analysis/register-axis.md
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REGISTER_FEATURES = ["de_rate", "disyllabic_ratio", "monosyllabic_ratio", "connective_rate",
                     "sent_initial_connective_ratio", "second_person_rate", "p_question",
                     "p_dash", "para_sents_mean", "sent_len_mean"]


def load() -> list[dict]:
    rows = list(csv.DictReader(open(HERE / (sys.argv[1] if len(sys.argv) > 1 else "features_clean.csv"))))
    for r in rows:
        for k in REGISTER_FEATURES:
            v = r.get(k, "")
            r[k] = float(v) if v not in ("", "nan") else np.nan
    return [r for r in rows if not any(np.isnan(r[k]) for k in REGISTER_FEATURES)]


def main() -> int:
    rows = load()
    X = np.array([[r[k] for k in REGISTER_FEATURES] for r in rows], float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-9] = 1.0
    Z = (X - mu) / sd

    def sel(src, reg):
        return np.array([i for i, r in enumerate(rows) if r["source"] == src and r["register"] == reg])

    hf, hi = sel("human", "formal"), sel("human", "informal")
    af, ai = sel("ai", "formal"), sel("ai", "informal")
    w = Z[hf].mean(0) - Z[hi].mean(0)
    w /= np.linalg.norm(w)
    proj = Z @ w
    mid = (proj[hf].mean() + proj[hi].mean()) / 2

    def stat(idx):
        v = proj[idx]
        return {"n": int(len(idx)), "median": round(float(np.median(v)), 3),
                "q25": round(float(np.percentile(v, 25)), 3),
                "q75": round(float(np.percentile(v, 75)), 3),
                "share_formal_side": round(float((v > mid).mean()), 3)}

    out = {"axis_weights": {k: round(float(x), 3) for k, x in zip(REGISTER_FEATURES, w)},
           "cells": {"human_formal": stat(hf), "human_informal": stat(hi),
                     "ai_formal": stat(af), "ai_informal": stat(ai)},
           "midpoint": round(float(mid), 3)}
    # distance of AI-informal median to each human register median
    out["ai_informal_gap"] = {
        "to_human_formal": round(abs(out["cells"]["ai_informal"]["median"] - out["cells"]["human_formal"]["median"]), 3),
        "to_human_informal": round(abs(out["cells"]["ai_informal"]["median"] - out["cells"]["human_informal"]["median"]), 3),
    }
    (HERE / "register-axis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    # freeze the reference so later runs (e.g. new checkpoints) use the SAME axis
    ref = {"features": REGISTER_FEATURES, "mu": mu.tolist(), "sd": sd.tolist(),
           "w": w.tolist(), "mid": float(mid)}
    (HERE / "reference.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1))

    c = out["cells"]
    md = ["# 语域轴投影：AI 有没有写错语域", "",
          "轴由**人类**两语域的均值差定义；正值=更接近人类正式，负值=更接近人类非正式。", "",
          "| 格 | n | 中位数 | 四分位 | 落在正式侧的比例 |", "|---|---|---|---|---|"]
    for k, v in c.items():
        md.append(f"| {k} | {v['n']} | {v['median']} | {v['q25']}–{v['q75']} | {v['share_formal_side']} |")
    g = out["ai_informal_gap"]
    md += ["", f"AI·非正式的中位数距人类正式 {g['to_human_formal']}，距人类非正式 {g['to_human_informal']}。", "",
           "轴权重（越大越偏正式）：", ""]
    for k, v in sorted(out["axis_weights"].items(), key=lambda kv: -abs(kv[1])):
        md.append(f"- {k}: {v}")
    (HERE / "register-axis.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "axis_weights"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
