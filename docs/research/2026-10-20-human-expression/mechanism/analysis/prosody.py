#!/usr/bin/env python3
"""韵律层：把"节奏"从句子长短换成汉语的音步/停延/单双音。

语言学审读指出的最大缺口：汉语里节奏是语法问题（冯胜利的语体语法），
句长 CV 只是排版的影子。本模块测四组量：

P1 停延结构：以标点为界的韵律短语长度（均值/CV/最长）、落在 2–5 音节的比例
P2 单双音配置：双音词比、单音词比、四字格比
P3 节律偏好：偶数音节短语比例（双步律的可测影子）
P4 虚化成分密度（的/了/着/过/们/儿/子），作为书面—口语连续统的代理

局限：音节按汉字近似（多音字、儿化、轻声未建模）；只作组间比较，不作单篇判定。

输出：analysis/prosody.json
"""
from __future__ import annotations

import json
import re
import statistics as st
from collections import Counter
from pathlib import Path

import jieba
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from human_model import BATCHES, load

CJK = re.compile(r"[\u4e00-\u9fff]")
CJK_TOKEN = re.compile(r"^[\u4e00-\u9fff]+$")
PHRASE_SPLIT = re.compile(r"[，。；：！？、\n\r]+")
WEAK = "的了着过们儿子"
OUT = Path(__file__).resolve().parent
PROS = ["phrase_len_mean", "phrase_len_cv", "phrase_len_max", "phrase_2_5_ratio",
        "disyllabic_ratio", "monosyllabic_ratio", "four_char_ratio",
        "even_phrase_ratio", "weak_particle_rate"]
SENT = ["sent_len", "sent_cv", "para_cv"]


def prosody_feats(text: str) -> dict:
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"[A-Za-z0-9_\-\./:%@#\$\{\}\[\]\|~^*+=<>\\]{2,}", "", t)
    phrases = [p for p in PHRASE_SPLIT.split(t) if len(CJK.findall(p)) >= 2]
    lens = [len(CJK.findall(p)) for p in phrases] or [0]
    toks = [w for w in jieba.lcut(t) if CJK_TOKEN.match(w)]
    n_tok = max(len(toks), 1)
    n_cjk = max(len(CJK.findall(t)), 1)
    mean = st.mean(lens)
    return {
        "phrase_len_mean": mean,
        "phrase_len_cv": st.pstdev(lens) / mean if mean else 0.0,
        "phrase_len_max": max(lens),
        "phrase_2_5_ratio": sum(1 for x in lens if 2 <= x <= 5) / len(lens),
        "disyllabic_ratio": sum(1 for w in toks if len(w) == 2) / n_tok,
        "monosyllabic_ratio": sum(1 for w in toks if len(w) == 1) / n_tok,
        "four_char_ratio": sum(1 for w in toks if len(w) == 4) / n_tok,
        "even_phrase_ratio": sum(1 for x in lens if x % 2 == 0) / len(lens),
        "weak_particle_rate": 1000 * sum(t.count(c) for c in WEAK) / n_cjk,
    }


def path_of(batch: str, doc: str, genre: str = "") -> Path | None:
    bdir = BATCHES[batch]
    name = doc.split("/")[-1]
    for f in (bdir / name, (bdir / genre / name) if genre else None):
        if f and f.exists():
            return f
    return None


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
    return float(np.mean(vals))


def ari_kmeans(rows: list[dict], keys: list[str]) -> float:
    X = np.array([[r[k] for k in keys] for r in rows], float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    X = (X - mu) / sd
    km = KMeans(n_clusters=5, n_init=20, random_state=0).fit(X)
    return float(adjusted_rand_score([r["genre"] for r in rows], km.labels_))


def main() -> int:
    base = load()
    res = {"groups": {}, "representations": {}}
    for b in ["human", "v1", "v2", "v3"]:
        rr = [r for r in base if r["batch"] == b]
        if len(rr) < 20:
            continue
        for r in rr:
            p = path_of(b, r["doc"], r["genre"])
            r.update(prosody_feats(p.read_text(encoding="utf-8", errors="ignore")) if p else {k: 0 for k in PROS})
        res["groups"][b] = {
            "n": len(rr),
            "mean": {k: round(st.mean([r[k] for r in rr]), 3) for k in PROS},
            "by_genre_disyllabic": {g: round(st.mean([r["disyllabic_ratio"] for r in rr if r["genre"] == g]), 3)
                                    for g in sorted({r["genre"] for r in rr})},
            "eta2_prosody": round(eta2(rr, PROS), 3),
            "eta2_sentence": round(eta2(rr, SENT), 3),
            "eta2_all21": round(eta2(rr, [k for k in r.keys() if k not in ("genre", "cjk", "doc", "batch")] ), 3),
            "ari_prosody": round(ari_kmeans(rr, PROS), 3),
            "ari_sentence": round(ari_kmeans(rr, SENT), 3),
        }
    OUT.joinpath("prosody.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    for b, v in res["groups"].items():
        print(f"{b:<6} n={v['n']:>3} 双音比 {v['mean']['disyllabic_ratio']:.3f} "
              f"四字格 {v['mean']['four_char_ratio']:.4f} 偶数短语 {v['mean']['even_phrase_ratio']:.3f} "
              f"2–5音节短语 {v['mean']['phrase_2_5_ratio']:.3f} | η²韵律 {v['eta2_prosody']:.3f} "
              f"η²句长 {v['eta2_sentence']:.3f} ARI韵律 {v['ari_prosody']:.2f} ARI句长 {v['ari_sentence']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
