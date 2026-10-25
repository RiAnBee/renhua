#!/usr/bin/env python3
"""Analyse returned blind-review CSVs (R1–R5 from design.md).

Input: data/*.csv with columns rater, blind_id, score (0-100), choice (a/b),
quote, seconds.
"""
from __future__ import annotations

import csv
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKT = HERE / "packet" / "items.json"


def icc2k(rows: list[dict]) -> float:
    """ICC(2,k) approximation for a fully crossed design."""
    items = sorted({r["blind_id"] for r in rows})
    raters = sorted({r["rater"] for r in rows})
    m = {(r["blind_id"], r["rater"]): r["score"] for r in rows}
    k = len(raters)
    item_means = [st.mean([m[(i, rr)] for rr in raters if (i, rr) in m]) for i in items]
    grand = st.mean(item_means)
    ms_between = k * sum((x - grand) ** 2 for x in item_means) / max(len(items) - 1, 1)
    ss_within = sum((m[(i, rr)] - st.mean([m[(i, x)] for x in raters if (i, x) in m])) ** 2
                    for i in items for rr in raters if (i, rr) in m)
    df_within = len(items) * (k - 1)
    ms_within = ss_within / max(df_within, 1)
    return (ms_between - ms_within) / (ms_between + (k - 1) * ms_within) if ms_between else 0.0


def spearman(x: list[float], y: list[float]) -> float:
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1
        return r
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main() -> int:
    items = {i["blind_id"]: i for i in json.loads(PKT.read_text())}
    rows = []
    for f in sorted((HERE / "data").glob("*.csv")):
        with f.open() as fh:
            for r in csv.DictReader(fh):
                if float(r.get("seconds") or 0) < 15:
                    continue
                rows.append({"rater": r["rater"], "blind_id": r["blind_id"],
                             "score": float(r["score"]), "choice": r.get("choice", "").strip().lower(),
                             "quote": (r.get("quote") or "").strip()})
    if not rows:
        print("没有数据")
        return 1
    by_group: dict[str, list[float]] = {}
    for r in rows:
        g = items[r["blind_id"]]["group"]
        by_group.setdefault(g, []).append(r["score"])
    out = {"n_records": len(rows), "n_raters": len({r["rater"] for r in rows}),
           "group_means": {g: round(st.mean(v), 1) for g, v in sorted(by_group.items())},
           "icc2k": round(icc2k(rows), 3)}
    choice_b = [r for r in rows if items[r["blind_id"]]["group"] == "B"]
    out["B_choice_a_rate"] = round(sum(1 for r in choice_b if r["choice"] == "a") / max(len(choice_b), 1), 2)
    out["R1_thick_minus_thin"] = round(out["group_means"].get("B", 0) - out["group_means"].get("A", 0), 1)
    out["R5_human_minus_thick"] = round(out["group_means"].get("H", 0) - out["group_means"].get("B", 0), 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    HERE.joinpath("results-reader.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
