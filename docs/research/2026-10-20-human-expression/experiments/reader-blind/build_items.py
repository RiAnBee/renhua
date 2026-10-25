#!/usr/bin/env python3
"""Build the blind-review packet from human / thin / thick corpora.

60 items (5 genres x 4 docs x 3 groups), rotated into 12 questionnaires of 20
items each, so every item is rated by about 4 people and no questionnaire mixes
two versions of the same topic.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
HUMAN = EXP.parent / "mechanism" / "data-prep" / "runs" / "human"
CJK_LIMIT = 250
SEED = 20261025


def window(t: str) -> str:
    out, seen = [], 0
    for ch in t:
        out.append(ch)
        if "\u4e00" <= ch <= "\u9fff":
            seen += 1
            if seen >= CJK_LIMIT:
                break
    return "".join(out).strip()


def load_group(path: Path, group: str) -> list[dict]:
    items = []
    for f in sorted(path.glob("*.txt")):
        if f.name.startswith("README"):
            continue
        text = window(f.read_text(encoding="utf-8", errors="ignore"))
        if len(text) < 150:
            continue
        items.append({"id": f"{group}:{f.stem}", "group": group, "genre": f.stem.split("-")[0],
                      "source": f.name, "text": text})
    return items


def main() -> int:
    rng = random.Random(SEED)
    groups = {
        "H": [],
        "A": load_group(EXP / "thick-context" / "raw" / "thin", "A"),
        "B": load_group(EXP / "thick-context" / "raw" / "thick", "B"),
    }
    for g in ["S1", "S2", "S3", "S4", "S5"]:
        files = sorted((HUMAN / g).glob("*.txt"))[:4]
        for f in files:
            text = window(f.read_text(encoding="utf-8", errors="ignore"))
            if len(text) >= 150:
                groups["H"].append({"id": f"H:{f.stem}", "group": "H", "genre": g,
                                    "source": f.name, "text": text})
    if len(groups["A"]) < 15 or len(groups["B"]) < 15:
        print("thin/thick 尚未齐备：", {k: len(v) for k, v in groups.items()})
        return 1

    by_genre = {}
    for grp, rows in groups.items():
        for r in rows:
            by_genre.setdefault(r["genre"], {}).setdefault(grp, []).append(r)
    picked = []
    for g, d in sorted(by_genre.items()):
        for grp in ("H", "A", "B"):
            items = d.get(grp, [])[:4]
            if len(items) < 4:
                print(f"警告：{g}/{grp} 只有 {len(items)} 篇")
            picked += items
    rng.shuffle(picked)
    for i, it in enumerate(picked, 1):
        it["blind_id"] = f"T{i:02d}"

    n_forms, per_form = 12, 20
    forms = [{"form": n + 1, "items": []} for n in range(n_forms)]
    for idx, it in enumerate(picked):
        for k in range(4):
            forms[(idx + k * 3) % n_forms]["items"].append(it["blind_id"])
    for f in forms:
        rng.shuffle(f["items"])

    out = HERE / "packet"
    out.mkdir(exist_ok=True)
    out.joinpath("items.json").write_text(json.dumps(
        [{"blind_id": it["blind_id"], "group": it["group"], "genre": it["genre"],
          "source": it["source"], "text": it["text"]} for it in picked],
        ensure_ascii=False, indent=1))
    out.joinpath("forms.json").write_text(json.dumps(forms, ensure_ascii=False, indent=1))
    print("items", len(picked), "forms", n_forms, "per form", per_form)
    print({g: len(v) for g, v in groups.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
