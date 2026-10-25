#!/usr/bin/env python3
"""Triage extracted texts into digestion batches with graded depth.

Tier decides reading depth:
  A  Chinese research, practice guides, reading-cognition, open books, supplements,
     citation audits -> full card set (3-8 cards per document)
  B  international theory / corpus / genre work -> condensed cards (1-3 per document)
  C1 work on style transfer, meaning preservation, human evaluation, readability,
     simplification -> one fidelity card per document (feeds the eval design)
  C2 remaining computational/detection papers ->登记 only, no cards

Scanned or broken files are routed to digest/needs_visual.jsonl instead.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RES = ROOT / "docs" / "research" / "2026-10-20-human-expression"
DIGEST = ROOT / ".harness" / "research-20261020" / "digest"
BRANCHES = ["linguistics-zh", "linguistics-intl", "practice-guides", "open-books",
            "reading-cognition", "supplements", "citation-audits"]

B_TOPICS = {
    "genre", "register", "pragmatics", "interaction", "academic-writing", "writing-process",
    "style-transfer", "mandarin", "topic", "given-new", "stance", "complexity", "revision",
    "rhetoric", "语域变异", "体裁", "语步", "标点", "学术写作", "写作连贯", "corpus", "cohesion",
    "information-structure", "coherence", "discourse-relations", "conversation-analysis",
    "scientific-writing", "audience", "readability", "cross-cultural-writing", "学术立场",
    "作者声音", "话语标记", "evaluation", "human-evaluation", "style", "voice", "syntax",
    "punctuation", "translation", "paraphrase", "semantic-preservation", "simplification",
}
C1_TITLE_HINTS = (
    "style transfer", "style-transfer", "meaning preservation", "semantic fidelity",
    "human evaluation", "readability", "simplification", "paraphrase", "rewrit",
    "formality transfer", "text style", "authorial", "edit",
)


def load_records() -> dict[str, dict]:
    recs = {}
    for b in BRANCHES:
        p = RES / b / "sources.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["_branch"] = b
                recs[r["id"]] = r
    return recs


def tier_of(rec: dict) -> str:
    branch = rec["_branch"]
    if branch in {"linguistics-zh", "practice-guides", "reading-cognition", "open-books",
                  "supplements", "citation-audits"}:
        return "A"
    topics = {str(t).lower() for t in (rec.get("topics") or [])}
    title = (rec.get("title") or "").lower()
    if topics & B_TOPICS:
        return "B"
    if any(h in title for h in C1_TITLE_HINTS):
        return "C1"
    return "C2"


def main() -> int:
    manifest = [json.loads(l) for l in (DIGEST / "text-manifest.jsonl").read_text().splitlines() if l.strip()]
    recs = load_records()
    readable = [m for m in manifest if m["quality"] in {"readable", "latin_only"}]
    needs_visual = [m for m in manifest if m["quality"] not in {"readable", "latin_only"}]

    groups: dict[str, list] = {"A": [], "B": [], "C1": [], "C2": []}
    for m in readable:
        rec = recs.get(m["id"], {"_branch": m["branch"]})
        tier = tier_of(rec)
        groups[tier].append({
            "id": m["id"], "tier": tier, "branch": m["branch"],
            "title": rec.get("title"), "authors": rec.get("authors"), "year": rec.get("year"),
            "language": rec.get("language"), "topics": rec.get("topics"),
            "text_file": m["text_file"], "pages": m["pages"], "chars": m["chars"],
            "cjk_chars": m["cjk_chars"], "existing_findings": rec.get("findings"),
            "existing_limits": rec.get("limitations"), "existing_implications": rec.get("renhua_implications"),
        })

    sizes = {"A": 8, "B": 10, "C1": 12, "C2": 20}
    out = DIGEST / "batches"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        if old.stem[0] in "abc" and not old.stem.startswith("d2"):
            old.unlink()
    index, batch_list = [], []
    for tier, items in groups.items():
        items.sort(key=lambda x: str(x["id"]))
        per = sizes[tier]
        for start in range(0, len(items), per):
            chunk = items[start:start + per]
            name = f"{tier.lower()}-{start // per:02d}"
            (out / f"{name}.json").write_text(json.dumps(chunk, ensure_ascii=False, indent=1))
            batch_list.append({"batch": name, "tier": tier, "documents": len(chunk)})
        index.extend(items)
    (DIGEST / "digest-index.jsonl").write_text(
        "\n".join(json.dumps(i, ensure_ascii=False) for i in index) + "\n")
    (DIGEST / "needs_visual.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in needs_visual) + "\n")
    (DIGEST / "batch-list.json").write_text(json.dumps(batch_list, ensure_ascii=False, indent=1))
    print(json.dumps({"batches": len(batch_list), "documents": len(index),
                      "tiers": {k: len(v) for k, v in groups.items()},
                      "needs_visual": len(needs_visual)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
