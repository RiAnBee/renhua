#!/usr/bin/env python3
"""Build the 2x2 form-layer items.

Factor 1 (genre label): explicit genre sentence vs neutral "写一篇文字".
Factor 2 (materials): full situation packet vs none.

Cells: A=S+G (genre+materials), B=S-G (genre only), C=W+G (materials only),
D=W-G (neither). 5 genres x 6 topics x 4 cells = 120 cells.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "thick-context"))
from items import BASE, ITEMS, TAIL, THICK  # noqa: E402

NEUTRAL = {
    "S1": "围绕「{topic}」写一篇约 800 字的文字。",
    "S2": "围绕「{topic}」写一篇约 700 字的文字。",
    "S3": "围绕「{topic}」写一篇约 700 字的文字。",
    "S4": "围绕「{topic}」写一篇约 800 字的文字。",
    "S5": "围绕「{topic}」写一篇约 700 字的文字。",
}

CELLS = {
    "A": ("genre", "materials"),
    "B": ("genre", "none"),
    "C": ("neutral", "materials"),
    "D": ("neutral", "none"),
}


def prompt(item: dict, cell: str) -> str:
    style, mat = CELLS[cell]
    head = (BASE if style == "genre" else NEUTRAL)[item["genre"]].format(topic=item["topic"])
    text = head + TAIL
    if mat == "materials":
        facts = "\n".join(f"{i+1}) {f}" for i, f in enumerate(item["facts"]))
        text += THICK.format(identity=item["identity"], reader=item["reader"], facts=facts,
                             known=item["known"], consequence=item["consequence"])
    return text


def main() -> int:
    rows = []
    for it in ITEMS:
        for cell in CELLS:
            rows.append({
                "id": f"{cell}:{it['id']}", "item": it["id"], "cell": cell,
                "style": CELLS[cell][0], "materials": CELLS[cell][1],
                "genre": it["genre"], "topic": it["topic"],
                "prompt": prompt(it, cell),
                "tokens": it["tokens"],
            })
    assert len(rows) == 120, len(rows)
    HERE.joinpath("items.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("cells", len(rows), {c: sum(1 for r in rows if r["cell"] == c) for c in CELLS})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
