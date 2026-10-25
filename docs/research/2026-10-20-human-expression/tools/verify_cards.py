#!/usr/bin/env python3
"""Machine-check digestion cards against the extracted source text.

Catches the failure mode that matters: a card whose quote is not in its source
(invented or silently rewritten evidence). Also reports duplicate claims and
records without cards.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DIGEST = ROOT / ".harness" / "research-20261020" / "digest"
PUNCT = re.compile(r"[\s\u3000·、，。；：！？,.;:!?\"“”‘’'()（）\[\]【】《》<>—…\-/\\|]+")


def norm(s: str) -> str:
    return PUNCT.sub("", s or "")


def main() -> int:
    index = {}
    idx_path = DIGEST / "digest-index.jsonl"
    if idx_path.exists():
        for line in idx_path.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                index[item["id"]] = item
    cards_dir = DIGEST / "cards"
    results = {"batches": {}, "failures": [], "total_cards": 0, "passed": 0}
    seen_claims = {}
    duplicated = []
    for batch_file in sorted(cards_dir.glob("*.jsonl")):
        batch = batch_file.stem
        cards = [json.loads(l) for l in batch_file.read_text().splitlines() if l.strip()]
        ok = 0
        for c in cards:
            results["total_cards"] += 1
            rec = index.get(c.get("record_id"))
            text_file = ROOT / rec["text_file"] if rec and rec.get("text_file") else None
            if not text_file or not text_file.exists():
                results["failures"].append({"batch": batch, "card": c.get("card_id"),
                                            "reason": "no_text_file"})
                continue
            source = norm(text_file.read_text())
            quote = norm(c.get("quote_snippet"))
            if not quote:
                results["failures"].append({"batch": batch, "card": c.get("card_id"),
                                            "reason": "empty_quote"})
                continue
            if quote in source:
                ok += 1
                results["passed"] += 1
            else:
                results["failures"].append({"batch": batch, "card": c.get("card_id"),
                                            "reason": "quote_not_in_source",
                                            "quote": c.get("quote_snippet")[:60]})
            key = (c.get("record_id"), norm(c.get("claim"))[:120])
            if key in seen_claims:
                duplicated.append({"card": c.get("card_id"), "dup_of": seen_claims[key]})
            else:
                seen_claims[key] = c.get("card_id")
        results["batches"][batch] = {"cards": len(cards), "quote_verified": ok}
    results["duplicate_claims"] = duplicated
    covered = {json.loads(l)["record_id"] for f in cards_dir.glob("*.jsonl")
               for l in f.read_text().splitlines() if l.strip()}
    results["records_covered"] = len(covered)
    results["records_uncovered"] = len([i for i in index if i not in covered])
    out = DIGEST / "verification.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    rate = results["passed"] / results["total_cards"] if results["total_cards"] else 0
    print(json.dumps({"cards": results["total_cards"], "quote_pass": round(rate, 3),
                      "failures": len(results["failures"]), "duplicates": len(duplicated),
                      "records_covered": results["records_covered"],
                      "records_uncovered": results["records_uncovered"]}, ensure_ascii=False))
    return 0 if not results["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
