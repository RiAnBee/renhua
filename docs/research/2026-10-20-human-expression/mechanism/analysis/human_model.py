#!/usr/bin/env python3
"""Human-centred analysis: how much of form is explained by situation depth.

Questions
---------
Q1  How much of the form variation is explained by genre (situation D1)?
Q2  Do AI documents keep the genre signature (nearest-centroid assignment)?
Q3  Is within-genre spread compressed relative to humans (situation depth)?
Q4  Does concrete reference (numbers, dates, quotes, conditions) track genre
    in humans, and does it collapse in AI?
Q5  How much do AI documents overlap the human genre distribution?

Output: analysis/human_model.json, analysis/human_model.md
"""
from __future__ import annotations

import json
import math
import re
import statistics as st
from collections import Counter
from pathlib import Path

import jieba
import numpy as np

ROOT = Path(__file__).resolve().parents[5]
RUNS = ROOT / "docs/research/2026-10-20-human-expression/mechanism/data-prep/runs"
OUT = Path(__file__).resolve().parent

GENRES = {"S1": "求是体", "S2": "新闻", "S3": "公文", "S4": "技术博客", "S5": "生活随笔"}
BATCHES = {
    "human": RUNS / "human",
    "v1": RUNS / "gpt-6.1-sol-v1",
    "v2": RUNS / "gpt-6.1-sol-v2-short",
    "v3": RUNS / "gpt-6.1-sol-v3-templated",
    "v4": RUNS / "gpt-6.1-sol",
}

CJK = re.compile(r"[\u4e00-\u9fff]")
CJK_TOKEN = re.compile(r"^[\u4e00-\u9fff]+$")
import os
WINDOW = int(os.environ.get("HUMAN_MODEL_WINDOW", "0"))
SENT_SPLIT = re.compile(r"[。！？]+")
CONNECTIVES = ["因为", "所以", "因此", "然而", "但是", "不过", "而且", "并且", "此外", "另外",
               "首先", "其次", "最后", "总之", "综上", "同时", "于是", "从而", "尽管", "虽然",
               "如果", "只要", "只有", "无论", "以便", "换言之", "也就是说", "由此可见", "值得注意"]
FORMULA = ["根据", "按照", "现将", "特此", "如下", "遵照", "鉴于", "为了", "落实", "进一步",
           "切实", "加强", "推进", "有关", "各单位", "现将有关事项通知如下"]
EVAL = ["打造", "赋能", "助力", "整合", "覆盖", "提升", "构建", "闭环", "生态", "体系",
        "最佳实践", "开箱即用", "一站式", "无缝", "强大", "丰富", "灵活", "高效", "优雅",
        "完善", "深入", "全面", "便捷", "智能", "极致"]
CONDITION = ["如果", "若", "除非", "一旦", "否则", "前提是", "除", "仅当", "只有", "只要"]
NEGATION = ["不", "未", "没有", "无", "并非", "未能", "尚未"]
PARTICLE = ["吧", "呢", "啊", "嘛", "哦", "呀", "啦", "嗯"]
TIME_RE = re.compile(r"\d{4}年|\d{1,2}月|\d{1,2}日|去年|今年|上月|本周|当日|日前|近年来")
YEAR_RE = re.compile(r"\d{4}")
NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")
QUOTE_RE = re.compile(r"[「『“\"][^」』”\"]{2,20}[」』”\"]")
BOOK_RE = re.compile(r"《[^》]{2,20}》")
INST_RE = re.compile(r"[\u4e00-\u9fff]{2,8}(?:公司|大学|学院|研究所|研究院|委员会|政府|集团|银行|医院|法院|检察院|部|厅|局|署|中心|协会|基金会)")
NOUN_SUF = re.compile(r"(性|化|度|主义|者|力|感)$")
PRON1 = ["我", "我们", "咱们", "本人"]
PRON2 = ["你", "你们", "您", "大家"]
STOP = set("的了是在和与及也就都而及其这那有着不我你他她它个上中下为以对从到之把被让给")


NOTICE = re.compile(
    r"^(?:您在使用一个|请更新你的浏览器|（平台提示|平台提示|转载请注明出处|责任编辑|微信扫一扫|扫码关注|本文来源|来源：|编辑：).{0,120}$",
    re.M)


def clean(t: str) -> str:
    """Strip markdown/code/url and site boilerplate so rates share a denominator.

    Collection artifact found 2026-10-25: all 12 S5 files open with a
    '您在使用一个旧版本的浏览器…' notice (plus a few other site notices in S1-S4).
    Left in, they occupy 10-14% of a 250-character window and bias every rate.
    """
    t = NOTICE.sub("", t)
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"(?m)^#{1,6}\s*", "", t)
    t = re.sub(r"(?m)^\s*([-*+>]\s+|\d+[.、]\s+)", "", t)
    return t


def window(text: str, n: int) -> str:
    out, seen = [], 0
    for ch in text:
        out.append(ch)
        if CJK.match(ch):
            seen += 1
            if seen >= n:
                break
    return "".join(out)


def feats(text: str) -> dict:
    t = clean(text)
    n = max(len(CJK.findall(t)), 1)
    sents = [s for s in SENT_SPLIT.split(t) if len(CJK.findall(s)) >= 2]
    lens = [len(CJK.findall(s)) for s in sents] or [0]
    paras = [p for p in t.split("\n") if len(CJK.findall(p)) >= 4]
    plens = [len(CJK.findall(p)) for p in paras] or [0]
    toks = [w for w in jieba.lcut(t) if CJK_TOKEN.match(w)]
    c = Counter(toks)
    per_k = lambda x: 1000.0 * x / n
    mean_len = st.mean(lens)
    cv = st.pstdev(lens) / mean_len if mean_len else 0.0
    pcv = st.pstdev(plens) / st.mean(plens) if st.mean(plens) else 0.0
    return {
        "cjk": n,
        "sent_len": mean_len,
        "sent_cv": cv,
        "para_cv": pcv,
        "connective": per_k(sum(t.count(w) for w in CONNECTIVES)),
        "sent_initial_conn": 100.0 * sum(1 for s in sents if any(s.strip().startswith(w) for w in CONNECTIVES)) / max(len(sents), 1),
        "formula": per_k(sum(t.count(w) for w in FORMULA)),
        "eval": per_k(sum(t.count(w) for w in EVAL)),
        "digit": per_k(len(NUM_RE.findall(t))),
        "year": per_k(len(YEAR_RE.findall(t))),
        "time": per_k(len(TIME_RE.findall(t))),
        "quote": per_k(len(QUOTE_RE.findall(t)) + len(BOOK_RE.findall(t))),
        "inst": per_k(len(INST_RE.findall(t))),
        "condition": per_k(sum(t.count(w) for w in CONDITION)),
        "negation": per_k(sum(t.count(w) for w in NEGATION)),
        "particle": per_k(sum(t.count(w) for w in PARTICLE)),
        "pron1": per_k(sum(t.count(w) for w in PRON1)),
        "pron2": per_k(sum(t.count(w) for w in PRON2)),
        "de": per_k(t.count("的")),
        "nominal": per_k(sum(1 for w in toks if len(w) >= 2 and NOUN_SUF.search(w))),
        "ttr": len(c) / max(len(toks), 1),
        "entropy": -sum((v / len(toks)) * math.log2(v / len(toks)) for v in c.values()) if toks else 0.0,
        "content": len(toks),
    }


REFERENCE = ["digit", "time", "year", "quote", "inst"]


def load() -> list[dict]:
    rows = []
    for bname, bdir in BATCHES.items():
        if not bdir.exists():
            continue
        for sub in sorted(bdir.iterdir()):
            if sub.is_dir():
                files, g = list(sub.glob("*.txt")), sub.name
            else:
                files, g = [sub], sub.stem.split("-")[0]
            for f in files:
                gid = f.stem.split("-")[0]
                if gid not in GENRES:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
                if len(CJK.findall(text)) < 200:
                    continue
                if WINDOW:
                    text = window(text, WINDOW)
                d = feats(text)
                d.update(doc=f"{bname}/{f.name}", batch=bname, genre=gid)
                rows.append(d)
    return rows


def eta2(rows: list[dict], key: str, group: str = "genre") -> float:
    vals = np.array([r[key] for r in rows], dtype=float)
    labels = [r[group] for r in rows]
    grand = vals.mean()
    ss_tot = ((vals - grand) ** 2).sum()
    if ss_tot == 0:
        return 0.0
    ss_b = 0.0
    for g in set(labels):
        v = vals[[i for i, l in enumerate(labels) if l == g]]
        ss_b += len(v) * (v.mean() - grand) ** 2
    return float(ss_b / ss_tot)


FEATURE_KEYS = ["sent_len", "sent_cv", "para_cv", "connective", "sent_initial_conn", "formula",
                "eval", "digit", "year", "time", "quote", "inst", "condition", "negation",
                "particle", "pron1", "pron2", "de", "nominal", "ttr", "entropy"]


def zmatrix(rows: list[dict], keys=FEATURE_KEYS) -> np.ndarray:
    X = np.array([[r[k] for k in keys] for r in rows], dtype=float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    return (X - mu) / sd


def centroid_stats(rows: list[dict]) -> dict:
    X = zmatrix(rows)
    labels = np.array([r["genre"] for r in rows])
    genres = sorted(set(labels))
    cents = {g: X[labels == g].mean(0) for g in genres}
    # nearest centroid leave-one-out
    correct = 0
    for i, r in enumerate(rows):
        g = labels[i]
        others = X[labels == g]
        if len(others) > 1:
            cent = (others.sum(0) - X[i]) / (len(others) - 1)
        else:
            cent = cents[g]
        d = {gg: float(np.linalg.norm(X[i] - (cent if gg == g else cents[gg]))) for gg in genres}
        if min(d, key=d.get) == g:
            correct += 1
    # silhouette
    sil = []
    for i in range(len(rows)):
        same = [j for j in range(len(rows)) if labels[j] == labels[i] and j != i]
        a = float(np.mean([np.linalg.norm(X[i] - X[j]) for j in same]))
        b = min(float(np.mean([np.linalg.norm(X[i] - X[j]) for j in range(len(rows)) if labels[j] == g]))
                for g in genres if g != labels[i])
        sil.append((b - a) / max(a, b))
    # within-genre mean pairwise distance
    within = {}
    for g in genres:
        idx = [i for i in range(len(rows)) if labels[i] == g]
        ds = [float(np.linalg.norm(X[i] - X[j])) for k, i in enumerate(idx) for j in idx[k + 1:]]
        within[g] = st.mean(ds) if ds else 0.0
    return {
        "n": len(rows),
        "loo_acc": correct / len(rows),
        "silhouette": st.mean(sil),
        "within_dist": within,
        "centroids": {g: cents[g] for g in genres},
    }


def assign_to_human(ai_rows: list[dict], human_stats: dict) -> dict:
    X = zmatrix(ai_rows + HROWS)[: len(ai_rows)]
    labels = [r["genre"] for r in ai_rows]
    hit = 0
    dists = []
    for i, g in enumerate(labels):
        d = {gg: float(np.linalg.norm(X[i] - human_stats["centroids"][gg])) for gg in human_stats["centroids"]}
        best = min(d, key=d.get)
        hit += int(best == g)
        dists.append((d[g], min(v for k, v in d.items() if k != g)))
    return {"assign_acc": hit / max(len(labels), 1),
            "own_dist": st.mean(x[0] for x in dists),
            "nearest_other": st.mean(x[1] for x in dists)}


def overlap(ai_rows: list[dict], human_rows: list[dict]) -> dict:
    Xh = zmatrix(human_rows + ai_rows)
    Xh, Xa = Xh[: len(human_rows)], Xh[len(human_rows):]
    lab = [r["genre"] for r in human_rows]
    out = {}
    for g in sorted(set(lab)):
        Hg = Xh[[i for i, l in enumerate(lab) if l == g]]
        mu = Hg.mean(0)
        cov = np.cov(Hg, rowvar=False) + np.eye(Hg.shape[1]) * 0.05
        inv = np.linalg.inv(cov)
        idx = [i for i, r in enumerate(ai_rows) if r["genre"] == g]
        if not idx:
            continue
        d = [float(((Xa[i] - mu) @ inv @ (Xa[i] - mu)) ** 0.5) for i in idx]
        hd = [float(((Hg[j] - mu) @ inv @ (Hg[j] - mu)) ** 0.5) for j in range(len(Hg))]
        thr = float(np.quantile(hd, 0.90))
        out[g] = {"ai_median_d": float(np.median(d)), "human_p90_d": thr,
                  "inside": float(np.mean([x <= thr for x in d]))}
    return out


HROWS: list[dict] = []


def main() -> int:
    global HROWS
    rows = load()
    HROWS = [r for r in rows if r["batch"] == "human"]
    per = {}
    for b in sorted({r["batch"] for r in rows}):
        rr = [r for r in rows if r["batch"] == b]
        per[b] = {"n": len(rr), "by_genre": Counter(r["genre"] for r in rr)}
    hs = centroid_stats(HROWS)

    res = {"n": len(rows), "per_batch": {k: {"n": v["n"], "by_genre": dict(v["by_genre"])} for k, v in per.items()},
           "human_loo_acc": hs["loo_acc"], "human_silhouette": hs["silhouette"],
           "within": {}}

    # Q1 eta^2 by genre inside each batch
    res["eta2"] = {}
    for b in sorted({r["batch"] for r in rows}):
        rr = [r for r in rows if r["batch"] == b]
        if len({r["genre"] for r in rr}) < 2:
            continue
        res["eta2"][b] = {k: round(eta2(rr, k), 3) for k in FEATURE_KEYS}

    # Q2 AI documents assigned to human genre centroids
    res["assign"] = {}
    for b in res["eta2"]:
        if b == "human":
            continue
        rr = [r for r in rows if r["batch"] == b]
        res["assign"][b] = assign_to_human(rr, hs)

    # Q3 within-genre spread, human vs AI
    for b in ["human", "v1", "v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if len(rr) < 20:
            continue
        X = zmatrix(rr)
        lab = [r["genre"] for r in rr]
        w = {}
        for g in sorted(set(lab)):
            idx = [i for i, l in enumerate(lab) if l == g]
            ds = [float(np.linalg.norm(X[i] - X[j])) for k, i in enumerate(idx) for j in idx[k + 1:]]
            w[g] = round(st.mean(ds), 2) if ds else 0.0
        res["within"][b] = w

    # Q3b geometry: distance to own genre centroid, centroid separation, silhouette
    res["geometry"] = {}
    for b in ["human", "v1", "v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if len(rr) < 20:
            continue
        X = zmatrix(rr)
        lab = np.array([r["genre"] for r in rr])
        gs = sorted(set(lab))
        cents = {g: X[lab == g].mean(0) for g in gs}
        own = []
        for i in range(len(rr)):
            idx = [j for j in range(len(rr)) if lab[j] == lab[i] and j != i]
            c = (X[idx].sum(0) / len(idx)) if idx else cents[lab[i]]
            own.append(float(np.linalg.norm(X[i] - c)))
        sep = [float(np.linalg.norm(cents[a] - cents[b])) for k, a in enumerate(gs) for b in gs[k + 1:]]
        sil = []
        for i in range(len(rr)):
            same = [j for j in range(len(rr)) if lab[j] == lab[i] and j != i]
            a = float(np.mean([np.linalg.norm(X[i] - X[j]) for j in same]))
            bmin = min(float(np.mean([np.linalg.norm(X[i] - X[j]) for j in range(len(rr)) if lab[j] == g]))
                       for g in gs if g != lab[i])
            sil.append((bmin - a) / max(a, bmin))
        wm = []
        for g in gs:
            idx = [i for i in range(len(rr)) if lab[i] == g]
            ds = [float(np.linalg.norm(X[i] - X[j])) for k, i in enumerate(idx) for j in idx[k + 1:]]
            wm.append(st.mean(ds) if ds else 0.0)
        res["geometry"][b] = {
            "own_centroid_dist": round(st.mean(own), 2),
            "between_centroid_dist": round(st.mean(sep), 2),
            "separation_ratio": round(st.mean(sep) / max(st.mean(own), 1e-9), 2),
            "silhouette": round(st.mean(sil), 3),
            "within_mean": round(st.mean(wm), 2),
        }

    # Q4 reference density by genre and batch
    ref = {}
    for b in ["human", "v1", "v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if not rr:
            continue
        ref[b] = {}
        for g in sorted({r["genre"] for r in rr}):
            gg = [r for r in rr if r["genre"] == g]
            ref[b][g] = round(st.mean(sum(r[k] for k in REFERENCE) for r in gg), 1)
    res["reference_total"] = ref
    res["reference_eta2"] = {b: round(eta2([r for r in rows if r["batch"] == b], "digit"), 3)
                             for b in ref if len({r["genre"] for r in rows if r["batch"] == b}) > 1}

    # Q5 overlap
    res["overlap"] = {}
    for b in ["v2", "v3"]:
        rr = [r for r in rows if r["batch"] == b]
        if len(rr) >= 20:
            res["overlap"][b] = overlap(rr, HROWS)

    OUT.joinpath("human_model" + (f"_w{WINDOW}" if WINDOW else "") + ".json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    print(json.dumps({k: res[k] for k in ("per_batch", "human_loo_acc", "human_silhouette")},
                     ensure_ascii=False, default=str))
    print("assign:", json.dumps(res["assign"], ensure_ascii=False))
    print("within:", json.dumps(res["within"], ensure_ascii=False))
    print("ref:", json.dumps(res["reference_total"], ensure_ascii=False))
    print("overlap:", json.dumps(res["overlap"], ensure_ascii=False))
    top = sorted(res["eta2"]["human"].items(), key=lambda kv: -kv[1])[:8]
    print("eta2 human top:", top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
