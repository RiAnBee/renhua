#!/usr/bin/env python3
"""Pre-registered dose-response analysis (0/2/5/10 facts).

Writes results.json + prints the verdict. Rules: preregistration.md §5.
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MECH = HERE.parents[1] / "mechanism" / "analysis"
sys.path.insert(0, str(MECH))

from human_model import feats  # noqa: E402
from prosody import prosody_feats  # noqa: E402

CJK = re.compile(r"[\u4e00-\u9fff]")
NUM = re.compile(r"\d+(?:\.\d+)?")
RAW = HERE / "raw"
BAD = ["作为AI", "作为 AI", "以下是", "希望对你有帮助", "```", "\n#", "\n- ", "\n* "]
CELLS = ["d0", "d2", "d5", "d10"]
DOSES = [0, 2, 5, 10]


def window(t: str, n: int = 250) -> str:
    out, seen = [], 0
    for ch in t:
        out.append(ch)
        if CJK.match(ch):
            seen += 1
            if seen >= n:
                break
    return "".join(out)


def norm_num(s: str) -> str:
    return s.replace("，", "").replace(",", "").replace(" ", "")


def load(cell: str, items: dict) -> tuple[list[dict], list]:
    rows, rejected = [], []
    for f in sorted((RAW / cell).glob("*.txt")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        ncjk = len(CJK.findall(text))
        if ncjk < 400:
            rejected.append((f.stem, f"cjk={ncjk}"))
            continue
        if any(b in text for b in BAD):
            rejected.append((f.stem, "format"))
            continue
        it = items[f.stem]
        w = window(text)
        d = feats(w)
        d.update(prosody_feats(w))
        facts_text = norm_num("".join(it["facts"]))
        nums = NUM.findall(norm_num(text))
        novel = [x for x in nums if x not in facts_text]
        avail = [t for t in it["tokens"] if norm_num(t) in facts_text]
        matched = sum(1 for t in avail if norm_num(t) in norm_num(text))
        d.update({
            "id": f.stem, "cell": cell, "dose": it["dose"], "genre": it["genre"], "text": w,
            "reference": sum(d[k] for k in ("digit", "time", "year", "quote", "inst")),
            "novel_per_1k": round(1000 * len(novel) / max(len(CJK.findall(text)), 1), 1),
            "coverage": round(matched / len(avail), 2) if avail else None,
        })
        rows.append(d)
    return rows, rejected


def summarize(rows: list[dict]) -> dict:
    refs = [r["reference"] for r in rows]
    return {
        "n": len(rows),
        "reference_median": round(st.median(refs), 1),
        "reference_mean": round(st.mean(refs), 1),
        "reference_iqr": [round(float(np.percentile(refs, 25)), 1), round(float(np.percentile(refs, 75)), 1)],
        "eval_rate": round(st.mean([r["eval"] for r in rows]), 1),
        "novel_num_per_1k": round(st.mean([r["novel_per_1k"] for r in rows]), 1),
        "coverage": (round(st.mean([r["coverage"] for r in rows if r["coverage"] is not None]), 2)
                     if any(r["coverage"] is not None for r in rows) else None),
        "sent_len": round(st.mean([r["sent_len"] for r in rows]), 1),
        "sent_cv": round(st.mean([r["sent_cv"] for r in rows]), 3),
        "disyllabic": round(st.mean([r["disyllabic_ratio"] for r in rows]), 3),
        "phrase_2_5": round(st.mean([r["phrase_2_5_ratio"] for r in rows]), 3),
    }


def fit_log(ref: dict) -> dict:
    x = np.log1p(np.array(DOSES, float))
    y = np.array([ref[d] for d in DOSES], float)
    b, a = np.polyfit(x, y, 1)
    pred = a + b * x
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - pred) ** 2).sum() / ss if ss else float("nan")
    margin = [ref[d] - ref[p] for p, d in zip(DOSES[:-1], DOSES[1:])]
    return {"a": round(float(a), 2), "b": round(float(b), 2), "r2": round(float(r2), 3),
            "slope_per_ln": round(float(b), 2), "marginal": [round(m, 1) for m in margin]}


def main() -> int:
    items = {r["item"]: r for r in json.loads(HERE.joinpath("items.json").read_text())}
    out = {"cells": {}, "rejected": {}}
    for cell in CELLS:
        rows, rej = load(cell, items)
        out["rejected"][cell] = rej
        out["cells"][cell] = summarize(rows) if rows else {}
        print(cell, json.dumps(out["cells"][cell], ensure_ascii=False))

    if not all(out["cells"][c] for c in CELLS):
        print("有档位为空，未判定")
        return 1

    ref = {d: out["cells"][f"d{d}"]["reference_median"] for d in DOSES}
    g1, g2, g3 = ref[2] - ref[0], ref[5] - ref[2], ref[10] - ref[5]
    ok_n = all(out["cells"][c]["n"] >= 25 for c in CELLS)
    verdict = {"ok_n": ok_n, "ref_curve": ref, "gains": [round(g1, 1), round(g2, 1), round(g3, 1)],
               "fit": fit_log(ref)}
    if not ok_n:
        verdict["error"] = "某档通过闸门不足 25 篇，按 §5.1 停止判定"
    else:
        verdict["H-D_rising"] = bool(g1 >= 2 and g2 >= 2)
        verdict["H-S_saturated_at_5"] = bool(g3 < 0.25 * (g1 + g2))
        verdict["H-S_open_at_10"] = bool(not verdict["H-S_saturated_at_5"] and g3 >= 2)
        verdict["H-E_substitution"] = bool(ref[5] > ref[0]
                                           and out["cells"]["d5"]["eval_rate"] < out["cells"]["d0"]["eval_rate"])
        lens = [out["cells"][c]["sent_len"] for c in CELLS]
        dis = [out["cells"][c]["disyllabic"] for c in CELLS]
        verdict["H-F_form_stable"] = bool(max(lens) - min(lens) < 8 and max(dis) - min(dis) < 0.02)
        n0 = out["cells"]["d0"]["novel_num_per_1k"]
        n2, n5 = out["cells"]["d2"]["novel_num_per_1k"], out["cells"]["d5"]["novel_num_per_1k"]
        verdict["H-N_materials_suppress_invention"] = bool(n0 >= 2 * n5 and n5 <= n2)
    out["verdict"] = verdict
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    HERE.joinpath("results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
