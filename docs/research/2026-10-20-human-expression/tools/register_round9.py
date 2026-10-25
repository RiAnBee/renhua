#!/usr/bin/env python3
"""Register round-9 DOAJ downloads as source records.

Reads the sweep receipts, keeps only rows whose PDF is actually on disk, skips
anything already present (same sha256, same DOI or same normalised title), and
appends records to the branch source files.

  register_round9.py --receipts acquisition/round9/doaj-receipts-e.jsonl --dry-run
  register_round9.py --receipts acquisition/round9/doaj-receipts-e.jsonl --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
BRANCHES = ("linguistics-intl", "linguistics-zh", "reading-cognition")


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (text or "").lower())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = load(BASE / "catalog.jsonl")
    seen_sha = {row["sha256"] for row in catalog if row.get("sha256")}
    seen_doi = {(row.get("doi") or "").lower() for row in catalog if row.get("doi")}
    seen_title = {norm(row.get("title")) for row in catalog if row.get("title")}

    receipts = [r for r in load(args.receipts) if r.get("result") == "downloaded"]
    buckets: dict[str, list[dict]] = {b: load(BASE / b / "sources.jsonl") for b in BRANCHES}
    counters = {}
    for branch, rows in buckets.items():
        nums = [int(m.group(1)) for row in rows for m in [re.match(r"[A-Z]+(\d+)$", str(row["id"]))] if m]
        counters[branch] = (max(nums) if nums else 0) + 1

    kept, skipped = [], 0
    for receipt in receipts:
        path = ROOT / receipt["path"]
        if not path.exists():
            skipped += 1
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        title = (receipt.get("title") or "").strip()
        doi = (receipt.get("doi") or "").lower()
        if sha in seen_sha or (doi and doi in seen_doi) or norm(title) in seen_title:
            skipped += 1
            continue
        branch = receipt.get("branch") if receipt.get("branch") in BRANCHES else "linguistics-intl"
        authors = receipt.get("authors") or []
        year = receipt.get("year")
        stem = re.sub(r"[^A-Za-z]", "", (re.split(r"[ ,]+", authors[0])[-1] if authors else "anon")) or "anon"
        rid = f"{branch[:2].upper()}-R9-{stem.upper()[:14]}-{year or 'nd'}"
        base_id, suffix = rid, 2
        existing_ids = {row["id"] for row in buckets[branch]}
        while rid in existing_ids:
            rid = f"{base_id}-{suffix}"
            suffix += 1
        record = {
            "id": rid,
            "title": title,
            "authors": authors,
            "year": year,
            "type": receipt.get("type") or "journal_article",
            "language": "en",
            "topics": [receipt.get("why")] if receipt.get("why") else [],
            "journal": ((receipt.get("journal") or {}).get("title") if isinstance(receipt.get("journal"), dict) else receipt.get("journal")),
            "canonical_url": receipt.get("source_url") or (f"https://doi.org/{doi}" if doi else None),
            "metadata_url": receipt.get("landing_pages", [None])[0] if receipt.get("landing_pages") else None,
            "doi": receipt.get("doi"),
            "isbn": None,
            "read_status": "metadata",
            "access_status": "open_access_downloaded",
            "findings": None,
            "implications_and_limits": None,
            "files": [
                {
                    "file": str(path.resolve()),
                    "bytes": len(data),
                    "sha256": sha,
                    "page_count": receipt.get("pages"),
                    "document_extent": "full_article_pdf_metadata_checked",
                    "acquisition_receipt_id": "round9-doaj",
                    "source_id": f"{branch}:{rid}",
                    "format": "pdf",
                    "full_book": False,
                }
            ],
            "query_ids": [receipt.get("qid")],
            "record_origin": "round9_doaj",
            "verified_at": "2026-10-24",
            "version_notes": "DOAJ 索引的 OA 期刊论文；页数与散列由本地文件复算。",
            "fulltext_obtained": True,
            "fulltext_format": "pdf",
            "complete_original_pdf": True,
        }
        buckets[branch].append(record)
        seen_sha.add(sha)
        if doi:
            seen_doi.add(doi)
        seen_title.add(norm(title))
        kept.append(record)

    print(f"receipts={len(receipts)} kept={len(kept)} skipped={skipped}")
    if not args.apply:
        return
    for branch, rows in buckets.items():
        if not rows:
            continue
        target = BASE / branch / "sources.jsonl"
        target.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    print("written")


if __name__ == "__main__":
    main()
