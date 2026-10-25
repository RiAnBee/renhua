#!/usr/bin/env python3
"""Pre-registered analysis for the thick-context experiment.

Reads raw/{thin,thick}/*.txt produced by run_api.py, applies the gate, computes
the registered metrics (P1–P5 + secondaries), runs the paired comparison, and
writes report.md + results.json.

Decision rules come from preregistration.md and are applied mechanically.
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
from prosody import PROS, prosody_feats  # noqa: E402

CJK = re.compile(r"[\u4e00-\u9fff]")
RAW = HERE / "raw"
BAD = ["作为AI", "以下是", "希望对你有帮助", "```", "\n#", "\n- ", "\n* ", "\n1. "]
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


def load_cond(cond: str, items: dict) -> list[dict]:
    rows, rejected = [], []
    for f in sorted((RAW / cond).glob("*.txt")):
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
        d.update({"id": f.stem, "genre": it["genre"], "cond": cond, "cjk_full": n,
                  "reference": sum(d[k] for k in ("digit", "time", "year", "quote", "inst")),
                  "coverage": sum(1 for tok in it["tokens"] if tok in text) / len(it["tokens"]),
                  "text": w})
        rows.append(d)
    return rows, rejected


def geometry(rows: list[dict]) -> dict:
    keys = FEATURE_KEYS
    X = np.array([[r[k] for k in keys] for r in rows], float)
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
    return {"n": len(rows), "eta2": round(eta2(rows, keys), 3), "silhouette": round(float(np.mean(sil)), 3),
            "kmeans_ari": round(float(adjusted_rand_score(lab, km.labels_)), 3)}


def main() -> int:
    items = {i["id"]: i for i in json.loads(HERE.joinpath("items.json").read_text())}
    res, rejects = {}, {}
    for cond in ("thin", "thick"):
        rows, rej = load_cond(cond, items)
        res[cond], rejects[cond] = rows, rej
        print(f"{cond}: {len(rows)} 通过，{len(rej)} 剔除", rej[:5])

    if len(res["thin"]) < 10 or len(res["thick"]) < 10:
        print("样本不足，先完成生成")
        return 1

    out = {"n": {k: len(v) for k, v in res.items()}, "rejected": rejects, "metrics": {}, "geometry": {}}
    for cond, rows in res.items():
        out["metrics"][cond] = {
            "reference_median": round(st.median([r["reference"] for r in rows]), 1),
            "coverage_mean": round(st.mean([r["coverage"] for r in rows]), 2),
            "sent_len": round(st.mean([r["sent_len"] for r in rows]), 1),
            "sent_cv": round(st.mean([r["sent_cv"] for r in rows]), 3),
            "eval_rate": round(st.mean([r["eval"] for r in rows]), 1),
            "disyllabic": round(st.mean([r["disyllabic_ratio"] for r in rows]), 3),
            "phrase_2_5": round(st.mean([r["phrase_2_5_ratio"] for r in rows]), 3),
            "cjk_full": round(st.mean([r["cjk_full"] for r in rows]), 0),
        }
        out["geometry"][cond] = geometry(rows)
        # style purity
        vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2)
        Xs = vec.fit_transform([mask_style(r["text"]) for r in rows])
        out["geometry"][cond]["style_purity"] = round(purity(cosine_similarity(Xs), [r["genre"] for r in rows]), 3)

    # paired comparison on P1
    by = {c: {r["id"]: r for r in rows} for c, rows in res.items()}
    common = sorted(set(by["thin"]) & set(by["thick"]))
    deltas = [by["thick"][i]["reference"] - by["thin"][i]["reference"] for i in common]
    out["paired"] = {
        "n_pairs": len(common),
        "median_delta_reference": round(st.median(deltas), 1),
        "frac_positive": round(sum(1 for d in deltas if d > 0) / max(len(deltas), 1), 2),
        "median_thin": round(st.median([by["thin"][i]["reference"] for i in common]), 1),
        "median_thick": round(st.median([by["thick"][i]["reference"] for i in common]), 1),
        "median_coverage_thin": round(st.median([by["thin"][i]["coverage"] for i in common]), 2),
        "median_coverage_thick": round(st.median([by["thick"][i]["coverage"] for i in common]), 2),
    }
    thin_ref = out["paired"]["median_thin"]
    cover = out["paired"]["median_coverage_thick"]
    ratio = out["paired"]["median_thick"] / thin_ref if thin_ref else float("inf")
    eta_drop = (out["geometry"]["thin"]["eta2"] - out["geometry"]["thick"]["eta2"]) / out["geometry"]["thin"]["eta2"]
    ari_drop = out["geometry"]["thin"]["kmeans_ari"] - out["geometry"]["thick"]["kmeans_ari"]
    h1 = ratio >= 2 and cover >= 0.6
    h2 = eta_drop >= 0.30 or ari_drop >= 0.10
    out["verdict"] = {"reference_ratio": round(ratio, 2), "coverage": cover,
                      "eta2_rel_drop": round(eta_drop, 2), "ari_drop": round(ari_drop, 3),
                      "H1_supported": bool(h1), "H2_supported": bool(h2)}
    HERE.joinpath("results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out["verdict"], ensure_ascii=False))
    print(json.dumps(out["paired"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
