#!/usr/bin/env python3
"""Robustness checks for the prototype-collapse claim.

R1  document length per batch (is the spread difference a length artefact?)
R2  bootstrap CI of the within-genre spread ratio (AI / human)
R3  lexical 6-gram Jaccard within genre vs across genres (independent of features)
R4  genre profile of concrete reference: does AI keep the ordering, at what level?
R5  caricature index: features where AI exaggerates the genre contrast
"""
from __future__ import annotations

import itertools
import json
import random
import re
import statistics as st
from pathlib import Path

import numpy as np

from human_model import (BATCHES, CJK, FEATURE_KEYS, REFERENCE, feats, load,
                         zmatrix)

OUT = Path(__file__).resolve().parent
random.seed(20261025)


def sixgrams(t: str) -> set[str]:
    s = re.sub(r"[^\u4e00-\u9fff]", "", t)
    return {s[i:i + 6] for i in range(len(s) - 5)}


def jac(a: set, b: set) -> float:
    return len(a & b) / max(len(a | b), 1)


def main() -> int:
    rows = load()
    res = {}

    # R1 length
    res["chars"] = {b: {"mean": round(st.mean([r["cjk"] for r in rows if r["batch"] == b]), 1),
                        "sd": round(st.pstdev([r["cjk"] for r in rows if r["batch"] == b]), 1)}
                    for b in sorted({r["batch"] for r in rows})}

    # R2 spread ratio with bootstrap
    def spread(rr):
        X = zmatrix(rr)
        lab = [r["genre"] for r in rr]
        ds = []
        for g in sorted(set(lab)):
            idx = [i for i, l in enumerate(lab) if l == g]
            ds += [float(np.linalg.norm(X[i] - X[j])) for k, i in enumerate(idx) for j in idx[k + 1:]]
        return st.mean(ds)

    human = [r for r in rows if r["batch"] == "human"]
    res["spread"] = {}
    for b in ["v1", "v2", "v3"]:
        ai = [r for r in rows if r["batch"] == b]
        if len(ai) < 20:
            continue
        obs = spread(ai) / spread(human)
        boot = []
        for _ in range(2000):
            hs = [r for g in sorted({x["genre"] for x in human}) for r in random.sample([x for x in human if x["genre"] == g], 10)]
            as_ = [r for g in sorted({x["genre"] for x in ai}) for r in random.sample([x for x in ai if x["genre"] == g], min(9, len([x for x in ai if x["genre"] == g])))]
            boot.append(spread(as_) / spread(hs))
        boot.sort()
        res["spread"][b] = {"ratio": round(obs, 2), "ci95": [round(boot[50], 2), round(boot[1949], 2)]}

    # R3 lexical overlap
    grams = {}
    for b in ["human", "v1", "v2", "v3", "v4"]:
        rr = [r for r in rows if r["batch"] == b]
        if len(rr) < 2:
            continue
        texts = {}
        for r in rr:
            p = Path(r["doc"])
            f = (BATCHES[b] / p.name) if b != "human" and (BATCHES[b] / p.name).exists() else None
            texts[r["doc"]] = None
        # load text directly from file paths recorded in doc field
        def path_of(r):
            bdir = BATCHES[r["batch"]]
            for f in (bdir / r["doc"].split("/")[-1], bdir / r["genre"] / r["doc"].split("/")[-1]):
                if f.exists():
                    return f
            return None
        within, across = [], []
        gsets = {}
        for r in rr:
            f = path_of(r)
            if not f:
                continue
            gsets[r["doc"]] = (r["genre"], sixgrams(f.read_text(encoding="utf-8", errors="ignore")))
        items = list(gsets.items())
        for (k1, (g1, s1)), (k2, (g2, s2)) in itertools.combinations(items, 2):
            (within if g1 == g2 else across).append(jac(s1, s2))
        if within:
            res.setdefault("jaccard", {})[b] = {
                "within": round(st.mean(within), 4),
                "across": round(st.mean(across), 4) if across else None,
                "ratio": round(st.mean(within) / max(st.mean(across), 1e-9), 2) if across else None,
            }

    # R4 reference profile
    prof = {}
    for b in ["human", "v1", "v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if not rr:
            continue
        prof[b] = {g: round(st.mean([sum(r[k] for k in REFERENCE) for r in rr if r["genre"] == g]), 1)
                   for g in sorted({r["genre"] for r in rr})}
    res["reference_profile"] = prof
    gs = list(prof.get("human", {}).keys())
    if gs:
        for b in ["v1", "v2", "v3"]:
            if b in prof:
                h = [prof["human"][g] for g in gs]
                a = [prof[b][g] for g in gs]
                # Spearman
                rh = {v: i for i, v in enumerate(sorted(h))}
                ra = {v: i for i, v in enumerate(sorted(a))}
                d2 = sum((rh[x] - ra[y]) ** 2 for x, y in zip(h, a))
                n = len(gs)
                res.setdefault("reference_rank_corr", {})[b] = round(1 - 6 * d2 / (n * (n * n - 1)), 2)
                res.setdefault("reference_level_ratio", {})[b] = round(sum(a) / sum(h), 2)

    # R5 caricature: feature-level genre contrast, AI vs human
    def contrast(rr):
        X = zmatrix(rr)
        lab = [r["genre"] for r in rr]
        gs_ = sorted(set(lab))
        out = {}
        for j, k in enumerate(FEATURE_KEYS):
            means = [X[[i for i, l in enumerate(lab) if l == g], j].mean() for g in gs_]
            out[k] = round(st.pstdev(means), 3)
        return out

    car = {"human": contrast([r for r in rows if r["batch"] == "human"])}
    for b in ["v1", "v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if len(rr) >= 20:
            car[b] = contrast(rr)
    res["genre_contrast"] = car
    res["caricature"] = {k: round(car["v2"][k] / max(car["human"][k], 1e-9), 2) for k in FEATURE_KEYS}

    OUT.joinpath("robustness.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
