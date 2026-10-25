#!/usr/bin/env python3
"""Pre-registered analysis for the 2x2 form-layer experiment (cells A-D).

Writes results.json and report.md numbers. Decision rules: preregistration.md §5.
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score
from sklearn.metrics.pairwise import cosine_similarity

HERE = Path(__file__).resolve().parent
MECH = HERE.parents[1] / "mechanism" / "analysis"
sys.path.insert(0, str(MECH))

from human_model import FEATURE_KEYS, feats  # noqa: E402
from prosody import prosody_feats  # noqa: E402

CJK = re.compile(r"[\u4e00-\u9fff]")
RAW = HERE / "raw"
BAD = ["作为AI", "作为 AI", "以下是", "希望对你有帮助", "```", "\n#", "\n- ", "\n* "]
MARKERS = ["通知", "通报", "通告", "公告", "本报讯", "记者获悉", "据悉", "编者按", "本报评论员", "现就"]
FUNC = set("的了是在和与及也就都而及其这那有着不我你他她它个上中下为以对从到之把被让给很更最又再还只才就是并且或但如果所因此然不过虽然而且以及")
PUNCT = set("，。；：？！、“”（）")


def mask_style(t: str) -> str:
    return "".join(ch if (ch in FUNC or ch in PUNCT) else "X" for ch in t)


def window(t: str, n: int = 250) -> str:
    out, seen = [], 0
    for ch in t:
        out.append(ch)
        if CJK.match(ch):
            seen += 1
            if seen >= n:
                break
    return "".join(out)


def purity(sim: np.ndarray, labels: list[str], k: int = 5) -> float:
    hit = 0
    for i in range(len(labels)):
        order = [j for j in np.argsort(-sim[i]) if j != i][:k]
        hit += sum(1 for j in order if labels[j] == labels[i]) / k
    return hit / len(labels)


def eta2(rows: list[dict], keys: list[str]) -> float:
    vals = []
    for k in keys:
        v = np.array([r[k] for r in rows], float)
        grand = v.mean()
        sst = ((v - grand) ** 2).sum()
        if sst == 0:
            continue
        lab = [r["genre"] for r in rows]
        ssb = sum(len([1 for l in lab if l == g]) *
                  (v[[i for i, l in enumerate(lab) if l == g]].mean() - grand) ** 2 for g in set(lab))
        vals.append(ssb / sst)
    return float(np.mean(vals)) if vals else float("nan")


def load_cell(cell: str, items: dict) -> tuple[list[dict], list]:
    rows, rejected = [], []
    for f in sorted((RAW / cell).glob("*.txt")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        n = len(CJK.findall(text))
        if n < 400:
            rejected.append((f.stem, f"cjk={n}"))
            continue
        if any(b in text for b in BAD):
            rejected.append((f.stem, "format"))
            continue
        it = items[f.stem]
        w = window(text)
        d = feats(w)
        d.update(prosody_feats(w))
        d.update({"id": f.stem, "genre": it["genre"], "cell": cell, "text": w,
                  "reference": sum(d[k] for k in ("digit", "time", "year", "quote", "inst")),
                  "coverage": sum(1 for tok in it["tokens"] if tok in text) / len(it["tokens"]),
                  "marker": int(any(m in text[:120] for m in MARKERS)),
                  "title_line": int(bool(text.strip().splitlines()) and
                                    len(text.strip().splitlines()[0]) <= 24 and
                                    text.strip().splitlines()[0][-1:] not in "。！？")})
        rows.append(d)
    return rows, rejected


def geometry(rows: list[dict]) -> dict:
    X = np.array([[r[k] for k in FEATURE_KEYS] for r in rows], float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Xz = (X - mu) / sd
    lab = np.array([r["genre"] for r in rows])
    km = KMeans(n_clusters=5, n_init=20, random_state=0).fit(Xz)
    sil = []
    for i in range(len(rows)):
        same = [j for j in range(len(rows)) if lab[j] == lab[i] and j != i]
        a = float(np.mean([np.linalg.norm(Xz[i] - Xz[j]) for j in same])) if same else 0.0
        b = min(float(np.mean([np.linalg.norm(Xz[i] - Xz[j]) for j in range(len(rows)) if lab[j] == g]))
                for g in set(lab) if g != lab[i])
        sil.append((b - a) / max(a, b))
    vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2)
    Xs = vec.fit_transform([mask_style(r["text"]) for r in rows])
    return {"n": len(rows), "eta2": round(eta2(rows, FEATURE_KEYS), 3),
            "silhouette": round(float(np.mean(sil)), 3),
            "kmeans_ari": round(float(adjusted_rand_score(lab, km.labels_)), 3),
            "style_purity": round(purity(cosine_similarity(Xs), list(lab)), 3)}


def main() -> int:
    items = {}
    for r in json.loads(HERE.joinpath("items.json").read_text()):
        items[r["item"]] = r
    out = {"cells": {}, "rejected": {}}
    data = {}
    for cell in "ABCD":
        rows, rej = load_cell(cell, items)
        data[cell], out["rejected"][cell] = rows, rej
        if not rows:
            continue
        out["cells"][cell] = {
            "n": len(rows),
            "reference_median": round(st.median([r["reference"] for r in rows]), 1),
            "coverage_mean": round(st.mean([r["coverage"] for r in rows]), 2),
            "eval_rate": round(st.mean([r["eval"] for r in rows]), 1),
            "sent_len": round(st.mean([r["sent_len"] for r in rows]), 1),
            "sent_cv": round(st.mean([r["sent_cv"] for r in rows]), 3),
            "disyllabic": round(st.mean([r["disyllabic_ratio"] for r in rows]), 3),
            "phrase_2_5": round(st.mean([r["phrase_2_5_ratio"] for r in rows]), 3),
            "marker_rate": round(st.mean([r["marker"] for r in rows]), 2),
            "title_rate": round(st.mean([r["title_line"] for r in rows]), 2),
            **geometry(rows),
        }
        print(cell, json.dumps(out["cells"][cell], ensure_ascii=False))

    if len(out["cells"]) < 4:
        print("单元不足，未判定")
        return 1

    a, c = out["cells"]["A"], out["cells"]["C"]
    conds = [x["n"] >= 25 for x in out["cells"].values()]
    if not all(conds):
        out["verdict"] = {"error": "某单元通过闸门不足 25 篇，按 §5.1 停止主判定"}
    else:
        hf1 = (c["eta2"] <= 0.30) or (a["eta2"] - c["eta2"] >= 0.10 and a["kmeans_ari"] - c["kmeans_ari"] >= 0.10)
        hf2 = (c["eta2"] >= 0.40 and abs(a["eta2"] - c["eta2"]) <= 0.05)
        hm = (c["reference_median"] >= 2 * max(out["cells"]["D"]["reference_median"], 1)
              and a["reference_median"] >= 2 * max(out["cells"]["B"]["reference_median"], 1))
        out["verdict"] = {
            "H-F1_prompt_driven": bool(hf1), "H-F2_prior_driven": bool(hf2), "H-M_materials": bool(hm),
            "eta2_A_vs_C": [a["eta2"], c["eta2"]],
            "ari_A_vs_C": [a["kmeans_ari"], c["kmeans_ari"]],
            "style_A_vs_C": [a["style_purity"], c["style_purity"]],
            "marker_C_vs_A": [c["marker_rate"], a["marker_rate"]],
        }
        print(json.dumps(out["verdict"], ensure_ascii=False, indent=1))
    HERE.joinpath("results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
