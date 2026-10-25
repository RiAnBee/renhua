#!/usr/bin/env python3
"""Independent replication of the geometry claim in a second domain.

Domain A (main study): 5 Chinese genres, 12 docs each.
Domain B (this script): project documentation — personal README, big-org README,
product landing pages. Different sources, different collection pipeline.

If "genre explains only a modest share and clusters overlap" is a property of
human expression rather than of domain A, it should reproduce here.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import numpy as np

from human_model import FEATURE_KEYS, feats, zmatrix

ROOT = Path(__file__).resolve().parents[5]
SLOP = ROOT / "docs/research/2026-10-20-human-expression/mechanism/data-prep/runs/slop"
OUT = Path(__file__).resolve().parent

GROUPS = {"human-readme": "github-human:", "bigorg": "github-big:", "landing": "web:"}


def main() -> int:
    rows = []
    for line in (SLOP / "manifest.jsonl").read_text().splitlines():
        r = json.loads(line)
        g = next((k for k, pre in GROUPS.items() if r["id"].startswith(pre)), None)
        if not g:
            continue
        p = SLOP / r["file"]
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        d = feats(text)
        if d["cjk"] < 300:
            continue
        d.update(doc=r["id"], batch="humanB", genre=g)
        rows.append(d)

    if len(rows) < 15:
        print("too few", len(rows))
        return 1

    X = zmatrix(rows)
    lab = np.array([r["genre"] for r in rows])
    gs = sorted(set(lab))
    cents = {g: X[lab == g].mean(0) for g in gs}
    own, within = [], {}
    for g in gs:
        idx = [i for i, l in enumerate(lab) if l == g]
        ds = [float(np.linalg.norm(X[i] - X[j])) for k, i in enumerate(idx) for j in idx[k + 1:]]
        within[g] = round(st.mean(ds), 2) if ds else None
        for i in idx:
            c = (X[[j for j in idx if j != i]].sum(0) / max(len(idx) - 1, 1))
            own.append(float(np.linalg.norm(X[i] - c)))
    sep = [float(np.linalg.norm(cents[a] - cents[b])) for k, a in enumerate(gs) for b in gs[k + 1:]]
    sil = []
    for i in range(len(rows)):
        same = [j for j in range(len(rows)) if lab[j] == lab[i] and j != i]
        a = float(np.mean([np.linalg.norm(X[i] - X[j]) for j in same])) if same else 0.0
        bmin = min(float(np.mean([np.linalg.norm(X[i] - X[j]) for j in range(len(rows)) if lab[j] == g]))
                   for g in gs if g != lab[i])
        sil.append((bmin - a) / max(a, bmin))

    eta = {}
    for k in FEATURE_KEYS:
        vals = np.array([r[k] for r in rows], float)
        grand = vals.mean()
        sst = ((vals - grand) ** 2).sum()
        ssb = sum(len([1 for l in lab if l == g]) * (vals[lab == g].mean() - grand) ** 2 for g in gs)
        eta[k] = round(float(ssb / sst), 3) if sst else 0.0

    res = {
        "n": len(rows),
        "by_group": {g: int((lab == g).sum()) for g in gs},
        "own_centroid_dist": round(st.mean(own), 2),
        "between_centroid_dist": round(st.mean(sep), 2),
        "separation_ratio": round(st.mean(sep) / max(st.mean(own), 1e-9), 2),
        "silhouette": round(st.mean(sil), 3),
        "within": within,
        "mean_eta2": round(st.mean(eta.values()), 3),
        "top_eta2": sorted(eta.items(), key=lambda kv: -kv[1])[:6],
    }
    OUT.joinpath("replication_docs.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
