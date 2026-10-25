#!/usr/bin/env python3
"""Does the "AI fingerprint" transfer across registers?

Three questions, one script:
  1. Within-register separability: how well can source (human/AI) be predicted by
     each phenotype family (surface tics vs information structure vs stance vs
     lexical typicality)?
  2. Cross-register transfer: train in one register, test in the other. If the
     fingerprint is register-bound, AUC drops sharply — the operational form of
     "fixed checklists misfire".
  3. Feature stability: which individual features keep the same sign in both
     registers, and which flip.

Model: L2-regularised logistic regression on standardised features,
5-fold stratified CV within register; transfer uses the full other register.

Outputs: analysis/classifier.md, analysis/classifier.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent

FAMILIES = {
    "M5_rhythm": ["sent_len_mean", "sent_len_cv", "para_sents_mean", "para_sents_cv",
                  "p_comma", "p_period", "p_semicolon", "p_dunhao", "p_question"],
    "M4_stance": ["hedge_rate", "booster_rate", "first_person_pl_rate", "second_person_rate"],
    "M3_reference": ["pronoun_rate", "de_rate", "bei_rate", "nominalization_rate", "connective_rate",
                     "sent_initial_connective_ratio"],
    "M2_infostructure": ["para_topic_overlap", "adjacent_topic_continuity"],
    "H1_typicality": ["type_token_ratio", "top50_share", "unigram_entropy", "self_repeat_5gram"],
    "M1_register_legit": ["monosyllabic_ratio", "disyllabic_ratio", "digit_rate"],
}
ALL = sorted({f for v in FAMILIES.values() for f in v})


def load():
    rows = list(csv.DictReader(open(HERE / (sys.argv[1] if len(sys.argv) > 1 else "features_clean.csv"))))
    for r in rows:
        for k in ALL:
            v = r.get(k, "")
            r[k] = float(v) if v not in ("", "nan") else np.nan
    return rows


def matrix(rows, feats):
    # drop features that are constant in this subset: a zero-variance column makes
    # StandardScaler produce inf and silently poisons the fit
    keep = [f for f in feats if np.nanstd([r[f] for r in rows]) > 1e-9]
    X = np.array([[r[f] for f in keep] for r in rows], dtype=float)
    y = np.array([1 if r["source"] == "ai" else 0 for r in rows])
    return np.nan_to_num(X, nan=0.0), y


def cv_auc(rows, feats, seed=0):
    X, y = matrix(rows, feats)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    aucs = []
    for tr, te in skf.split(X, y):
        sc = StandardScaler().fit(X[tr])
        sc.scale_ = np.where(sc.scale_ < 1e-9, 1.0, sc.scale_)
        clf = LogisticRegression(max_iter=2000, C=0.5).fit(sc.transform(X[tr]), y[tr])
        aucs.append(roc_auc_score(y[te], clf.predict_proba(sc.transform(X[te]))[:, 1]))
    return float(np.mean(aucs))


def transfer(train_rows, test_rows, feats):
    Xa, ya = matrix(train_rows, feats)
    Xb, yb = matrix(test_rows, feats)
    sc = StandardScaler().fit(Xa)
    sc.scale_ = np.where(sc.scale_ < 1e-9, 1.0, sc.scale_)
    clf = LogisticRegression(max_iter=2000, C=0.5).fit(sc.transform(Xa), ya)
    return float(roc_auc_score(yb, clf.predict_proba(sc.transform(Xb))[:, 1]))


def main() -> int:
    rows = load()
    sets = dict(FAMILIES)
    sets["ALL"] = ALL
    formal = [r for r in rows if r["register"] == "formal"]
    informal = [r for r in rows if r["register"] == "informal"]
    out = {"n_formal": len(formal), "n_informal": len(informal), "families": {}}
    for name, feats in sets.items():
        out["families"][name] = {
            "auc_formal": round(cv_auc(formal, feats), 3),
            "auc_informal": round(cv_auc(informal, feats), 3),
            "auc_pooled": round(cv_auc(rows, feats), 3),
            "transfer_formal_to_informal": round(transfer(formal, informal, feats), 3),
            "transfer_informal_to_formal": round(transfer(informal, formal, feats), 3),
        }
    # per-feature sign stability
    signs = {}
    for f in ALL:
        a = np.array([r[f] for r in rows if r["source"] == "ai" and r["register"] == "formal"])
        h = np.array([r[f] for r in rows if r["source"] == "human" and r["register"] == "formal"])
        ai_ = np.array([r[f] for r in rows if r["source"] == "ai" and r["register"] == "informal"])
        hi = np.array([r[f] for r in rows if r["source"] == "human" and r["register"] == "informal"])
        d_f = np.nanmean(a) - np.nanmean(h)
        d_i = np.nanmean(ai_) - np.nanmean(hi)
        signs[f] = {"diff_formal": round(float(d_f), 3), "diff_informal": round(float(d_i), 3),
                    "stable": bool(np.sign(d_f) == np.sign(d_i))}
    out["feature_stability"] = signs
    out["n_stable"] = sum(1 for v in signs.values() if v["stable"])
    out["n_features"] = len(signs)
    (HERE / (f"classifier_{Path(sys.argv[1]).stem}.json" if len(sys.argv) > 1 else "classifier.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1))

    md = ["# 可分性与跨语域迁移（来源=人/AI）", "",
          f"正式 {len(formal)} 篇、非正式 {len(informal)} 篇；5 折分层交叉验证 AUC。", "",
          "| 特征族 | 正式内 | 非正式内 | 合并 | 正式→非正式 | 非正式→正式 |",
          "|---|---|---|---|---|---|"]
    for name, v in out["families"].items():
        md.append(f"| {name} | {v['auc_formal']} | {v['auc_informal']} | {v['auc_pooled']} | "
                  f"{v['transfer_formal_to_informal']} | {v['transfer_informal_to_formal']} |")
    md += ["", f"## 方向稳定性：{out['n_stable']}/{out['n_features']} 个特征在两语域同向", "",
           "| 特征 | 正式内差(ai-human) | 非正式内差 | 同向 |", "|---|---|---|---|"]
    for f, v in sorted(signs.items(), key=lambda kv: -abs(kv[1]["diff_formal"])):
        md.append(f"| {f} | {v['diff_formal']} | {v['diff_informal']} | {'是' if v['stable'] else '**否**'} |")
    (HERE / (f"classifier_{Path(sys.argv[1]).stem}.md" if len(sys.argv) > 1 else "classifier.md")).write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "feature_stability"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
