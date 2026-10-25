#!/usr/bin/env python3
"""Extract phenotype features from the four-cell Chinese corpus.

Design: source (human / ai) x register (formal / informal), 266 documents.
The features operationalise the phenotype layer M1-M5 of the mechanism protocol:
M1 register legitimacy, M2 information structure, M3 reference/cohesion,
M4 stance homogeneity, M5 rhythm. Surface tics are included so the analysis can
test whether they explain source better than the structural features do.

Output: analysis/features.csv (one row per document) and analysis/extract-log.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path

import jieba

ROOT = Path(__file__).resolve().parents[5]
CORPUS = ROOT / "corpus"
OUT = Path(__file__).resolve().parent

CONNECTIVES = ["因为", "所以", "因此", "然而", "但是", "不过", "而且", "并且", "此外", "另外",
               "首先", "其次", "再次", "最后", "总之", "综上", "同时", "同时", "于是", "从而",
               "尽管", "虽然", "即使", "如果", "只要", "只有", "无论", "不管", "以便", "以免",
               "与此同时", "换言之", "也就是说", "值得注意的是", "更重要的是", "由此可见"]
HEDGES = ["可能", "或许", "大概", "似乎", "也许", "一定程度上", "某种程度上", "据说", "据称",
          "恐怕", "未必", "不一定", "应该是", "倾向于"]
BOOSTERS = ["显然", "必然", "无疑", "一定", "必须", "充分", "高度", "极其", "完全", "绝对",
            "毫无疑问", "毫无疑问", "众所周知", "至关重要", "尤为"]
PRONOUNS = ["他", "她", "它", "他们", "她们", "它们", "这", "那", "这些", "那些", "其", "该"]
NOMINAL_SUFFIX = re.compile(r"(性|化|度|主义|者|力|感)$")
PUNCT = {"comma": "，", "period": "。", "semicolon": "；", "dunhao": "、", "colon": "：",
         "dash": "—", "ellipsis": "…", "quote": "“", "question": "？", "excl": "！"}
SENT_SPLIT = re.compile(r"[。！？；]+")
CJK = re.compile(r"[\u4e00-\u9fff]")
STOP = set("的了是在和与及也就都而及其这那有着不我你他她它个上中下为以对从到")


def sanitize(t: str) -> str:
    """Remove markdown/code/URLs so character-based rates are not diluted by
    non-prose content. AI informal documents contain code fences in 36/40 files
    (CJK share 0.34) versus 1/82 for human informal (0.61) — without this the
    denominator differs by cell and every per-character rate is biased."""
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"<[^>]{1,80}>", "", t)
    t = re.sub(r"(?m)^#{1,6}\s*", "", t)
    t = re.sub(r"(?m)^\s*([-*+]\s+|\d+[.、]\s+|>\s*)", "", t)
    t = re.sub(r"[A-Za-z0-9_\-\./:%@#\$\{\}\[\]\|~^*+=<>\\]{2,}", "", t)
    return t


def clean(t: str) -> str:
    t = re.sub(r"(?m)^#{1,6}\s*", "", t)
    t = re.sub(r"(?m)^\s*([-*+]\s+|\d+[.、]\s+|>\s*)", "", t)
    t = re.sub(r"\*\*|__", "", t)
    t = re.sub(r"[ \t\u3000]+", "", t)
    return t.strip()


def content_tokens(text: str) -> list[str]:
    toks = [w for w in jieba.cut(text) if w.strip() and CJK.search(w) and w not in STOP and len(w) <= 6]
    return toks


def entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if not total:
        return 0.0
    return -sum((c / total) * math.log(c / total + 1e-12) for c in counter.values())


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def token_counts(tokens: list[str], lexicon: list[str]) -> int:
    """Exact token matches: substring counting inflates 的 (目的/有的), 同时 (与此同时), 你 (你们)."""
    vocab = set(lexicon)
    return sum(1 for w in tokens if w in vocab)


def features(text: str) -> dict:
    text = clean(sanitize(text))
    n = max(len(text), 1)
    sents = [s for s in SENT_SPLIT.split(text) if len(s.strip()) > 3]
    paras = [p for p in text.split("\n") if len(p.strip()) > 10]
    toks = content_tokens(text)
    all_toks = [w for w in jieba.cut(text) if w.strip()]
    f = {"chars": len(text), "n_sents": len(sents), "n_paras": len(paras)}

    # M5 rhythm
    sl = [len(s) for s in sents] or [0]
    f["sent_len_mean"] = statistics.mean(sl)
    f["sent_len_cv"] = statistics.pstdev(sl) / (statistics.mean(sl) or 1)
    pl = [len([s for s in SENT_SPLIT.split(p) if len(s.strip()) > 3]) for p in paras] or [1]
    f["para_sents_mean"] = statistics.mean(pl)
    f["para_sents_cv"] = statistics.pstdev(pl) / (statistics.mean(pl) or 1)

    # punctuation profile (per 100 chars)
    for k, ch in PUNCT.items():
        f[f"p_{k}"] = text.count(ch) * 100 / n

    # M1/M4 lexical stance
    f["connective_rate"] = token_counts(all_toks, CONNECTIVES) * 1000 / n
    f["hedge_rate"] = token_counts(all_toks, HEDGES) * 1000 / n
    f["booster_rate"] = token_counts(all_toks, BOOSTERS) * 1000 / n
    init = sum(1 for s in sents if any(s.strip().startswith(w) for w in CONNECTIVES))
    f["sent_initial_connective_ratio"] = init / max(len(sents), 1)

    # reference / deixis
    f["pronoun_rate"] = token_counts(all_toks, PRONOUNS) * 1000 / n
    f["first_person_pl_rate"] = token_counts(all_toks, ["我们"]) * 1000 / n
    f["second_person_rate"] = token_counts(all_toks, ["你", "您", "你们"]) * 1000 / n
    f["bei_rate"] = token_counts(all_toks, ["被"]) * 1000 / n
    f["de_rate"] = token_counts(all_toks, ["的"]) * 1000 / n
    f["nominalization_rate"] = sum(1 for w in toks if NOMINAL_SUFFIX.search(w)) * 1000 / max(len(toks), 1)
    f["digit_rate"] = sum(ch.isdigit() for ch in text) * 100 / n

    # lexical concentration / typicality proxy
    c = Counter(toks)
    f["content_tokens"] = len(toks)
    f["type_token_ratio"] = len(c) / max(len(toks), 1)
    f["top50_share"] = sum(v for _, v in c.most_common(50)) / max(sum(c.values()), 1)
    f["unigram_entropy"] = entropy(c)
    f["disyllabic_ratio"] = sum(1 for w in toks if len(w) == 2) / max(len(toks), 1)
    f["monosyllabic_ratio"] = sum(1 for w in toks if len(w) == 1) / max(len(toks), 1)

    # self repetition (5-gram over characters)
    grams = [text[i:i + 5] for i in range(0, max(len(text) - 5, 0), 5)]
    gc = Counter(grams)
    f["self_repeat_5gram"] = (sum(v - 1 for v in gc.values() if v > 1)) / max(len(grams), 1)

    # M2 information structure: topic overlap between a paragraph's first sentence and the rest
    overlaps = []
    for p in paras:
        ps = [s for s in SENT_SPLIT.split(p) if len(s.strip()) > 3]
        if len(ps) < 2:
            continue
        head = set(content_tokens(ps[0]))
        rest = set(content_tokens("".join(ps[1:])))
        overlaps.append(jaccard(head, rest))
    f["para_topic_overlap"] = statistics.mean(overlaps) if overlaps else float("nan")

    # adjacent sentence topic continuity
    cont = []
    for a, b in zip(sents, sents[1:]):
        cont.append(jaccard(set(content_tokens(a)), set(content_tokens(b))))
    f["adjacent_topic_continuity"] = statistics.mean(cont) if cont else float("nan")
    return f


def windowed(text: str, width: int = 600, stride: int = 300) -> dict:
    """Average features over fixed-width windows.

    Document length differs sharply between cells (human formal ~2200 chars vs
    AI formal ~840), and lexical/rhythm features are length-sensitive. Fixed
    windows remove that confound; overlapping windows keep sample size usable.
    """
    clean_t = clean(sanitize(text))
    if len(clean_t) <= width:
        return features(clean_t)
    wins = []
    for start in range(0, len(clean_t) - width + 1, stride):
        wins.append(features(clean_t[start:start + width]))
    if not wins:
        return features(clean_t)
    keys = wins[0].keys()
    out = {}
    for k in keys:
        vals = [w[k] for w in wins if not (isinstance(w[k], float) and w[k] != w[k])]
        out[k] = statistics.mean(vals) if vals else float("nan")
    out["n_windows"] = len(wins)
    return out


def main() -> int:
    rows = []
    jieba.setLogLevel(20)
    for cell in ["formal", "informal", "ai_formal", "ai_informal"]:
        d = CORPUS / cell
        for p in sorted(d.glob("*.txt")):
            t = p.read_text(errors="ignore")
            if len(t.strip()) < 100:
                continue
            r = windowed(t)
            r.update({"doc": p.stem, "cell": cell,
                      "source": "ai" if cell.startswith("ai_") else "human",
                      "register": "informal" if "informal" in cell else "formal"})
            rows.append(r)
    cols = ["doc", "cell", "source", "register"] + [k for k in rows[0] if k not in {"doc", "cell", "source", "register"}]
    with open(OUT / "features_v3.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    log = {"docs": len(rows), "cells": Counter(r["cell"] for r in rows)}
    (OUT / "extract-log-v3.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    print(json.dumps(log, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
