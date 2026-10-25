#!/usr/bin/env python3
"""Independent check of the cluster-geometry claims with NO hand-made features.

The main analysis uses 21 curated features. This script re-tests the same claims
with character n-gram TF-IDF cosine similarity, which involves no feature choice
at all, plus a topic proxy to test whether AI within-genre similarity could be a
topic artefact rather than a style artefact.

Outputs: analysis/independent_check.json
"""
from __future__ import annotations

import json
import random
import re
import statistics as st
from pathlib import Path

import jieba
import jieba.posseg as pseg
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from human_model import BATCHES, clean

OUT = Path(__file__).resolve().parent
CJK = re.compile(r"[\u4e00-\u9fff]")
random.seed(3)


def load():
    docs = []
    for b, d in BATCHES.items():
        if not d.exists():
            continue
        for f in sorted(list(d.rglob("*.txt"))):
            if f.name.startswith("README"):
                continue
            gid = f.stem.split("-")[0]
            if gid not in {"S1", "S2", "S3", "S4", "S5"}:
                continue
            t = clean(f.read_text(encoding="utf-8", errors="ignore"))
            if len(CJK.findall(t)) < 200:
                continue
            if len(CJK.findall(t)) > 250:
                # match the 250-CJK window used in the main analysis
                out, seen = [], 0
                for ch in t:
                    out.append(ch)
                    if CJK.match(ch):
                        seen += 1
                        if seen >= 250:
                            break
                t = "".join(out)
            docs.append({"text": t, "genre": gid, "batch": b, "doc": f"{b}/{f.name}"})
    return docs


def purity(sim: np.ndarray, labels: list[str], k: int = 5) -> float:
    n = len(labels)
    hit = 0
    for i in range(n):
        order = [j for j in np.argsort(-sim[i]) if j != i][:k]
        hit += sum(1 for j in order if labels[j] == labels[i]) / k
    return hit / n


def top_purity(sim: np.ndarray, labels: list[str]) -> float:
    n = len(labels)
    hit = 0
    for i in range(n):
        order = [j for j in np.argsort(-sim[i]) if j != i][:1]
        hit += int(labels[order[0]] == labels[i])
    return hit / n


def within_dist(sim: np.ndarray, labels: list[str]) -> dict:
    out = {}
    for g in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == g]
        d = [1 - sim[i, j] for k, i in enumerate(idx) for j in idx[k + 1:]]
        out[g] = round(st.mean(d), 4) if d else None
    return out


def topic_overlap(docs: list[dict]) -> dict:
    """Share of top-20 content words, within vs across genre (topic proxy)."""
    vocab = []
    for d in docs:
        words = [w for w, flag in pseg.cut(d["text"]) if flag.startswith(("n", "v")) and len(w) > 1]
        d["heads"] = set(w for w, _ in sorted(
            {w: words.count(w) for w in set(words)}.items(), key=lambda kv: -kv[1])[:20])
    within, across = [], []
    for i, a in enumerate(docs):
        for b in docs[i + 1:]:
            j = len(a["heads"] & b["heads"]) / max(len(a["heads"] | b["heads"]), 1)
            (within if a["genre"] == b["genre"] else across).append(j)
    return {"within": round(st.mean(within), 4), "across": round(st.mean(across), 4)}


FUNC = set("的了是在和与及也就都而及其这那有着不我你他她它个上中下为以对从到之把被让给很更最又再还只才就是并且或但如果所因此然不过虽然而且以及")
PUNCT = set("，。；：？！、“”（）")


def mask_style(t: str) -> str:
    """Keep function words and punctuation, mask content characters.

    Isolates syntactic/style frames from topic words, so genre purity cannot be
    carried by shared content.
    """
    return "".join(ch if (ch in FUNC or ch in PUNCT) else "X" for ch in t)


def main() -> int:
    docs = load()
    res = {}
    vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=200000)
    for b in ["human", "v1", "v2", "v3"]:
        sub = [d for d in docs if d["batch"] == b]
        if len(sub) < 20:
            continue
        X = vec.fit_transform([d["text"] for d in sub])
        sim = cosine_similarity(X)
        labels = [d["genre"] for d in sub]
        perm = []
        for _ in range(100):
            lab = labels[:]
            random.shuffle(lab)
            perm.append(purity(sim, lab, 5))
        km = KMeans(n_clusters=5, n_init=20, random_state=0).fit(X)
        style_vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2)
        Xs = style_vec.fit_transform([mask_style(d["text"]) for d in sub])
        sim_s = cosine_similarity(Xs)
        perm_s = []
        for _ in range(50):
            lab = labels[:]
            random.shuffle(lab)
            perm_s.append(purity(sim_s, lab, 5))
        res[b] = {
            "n": len(sub),
            "ari_kmeans5": round(adjusted_rand_score(labels, km.labels_), 3),
            "kmeans_silhouette": round(float(silhouette_score(X, km.labels_, metric="cosine")), 3),
            "style_purity5": round(purity(sim_s, labels, 5), 3),
            "style_purity5_chance": round(st.mean(perm_s), 3),
            "purity5": round(purity(sim, labels, 5), 3),
            "purity5_chance": round(st.mean(perm), 3),
            "top1": round(top_purity(sim, labels), 3),
            "within_cosdist": within_dist(sim, labels),
            "topic": topic_overlap(sub),
        }
        print(b, json.dumps({k: v for k, v in res[b].items() if k != "topic"}, ensure_ascii=False),
              "topic", res[b]["topic"])
    OUT.joinpath("independent_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
