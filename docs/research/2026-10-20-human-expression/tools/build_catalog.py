#!/usr/bin/env python3
"""Rebuild the cross-branch index without rewriting any source records.

Run from the renhua root. Uses only the standard library. Exact DOI/ISBN/URL
matches are groups for review, not silent assertions that editions are equal.
"""
import collections
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/research/2026-10-20-human-expression"
BRANCHES = ["linguistics-zh", "linguistics-intl", "reading-cognition",
            "practice-guides", "open-books", "citation-audits", "supplements"]


def group_key(record, record_id):
    doi = record.get("doi")
    if isinstance(doi, str) and doi.strip():
        doi = re.sub(r"^https?://(?:dx\.)?doi.org/", "", doi.strip(), flags=re.I)
        if doi.startswith("10."):
            return "doi:" + doi.lower()
    isbn = record.get("isbn")
    if isinstance(isbn, str) and isbn.strip():
        return "isbn:" + re.sub(r"[^0-9Xx]", "", isbn).upper()
    url = record.get("canonical_url") or record.get("metadata_url")
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        parts = urlsplit(url)
        path = unquote(parts.path).rstrip("/")
        return "url:" + urlunsplit(("https", parts.netloc.lower(), path, parts.query, ""))
    return "record:" + record_id


def main():
    records, errors, pending, warnings = [], [], [], []
    counts = {}
    for branch in BRANCHES:
        source = BASE / branch / "sources.jsonl"
        if not source.exists():
            pending.append(branch)
            continue
        seen = set()
        branch_rows = []
        for lineno, line in enumerate(source.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{source.relative_to(ROOT)}:{lineno}: {exc}")
                continue
            source_id = row.get("id")
            if not source_id or source_id in seen:
                errors.append(f"{branch}:{lineno}: missing or duplicate id {source_id}")
            seen.add(source_id)
            record_id = branch + ":" + str(source_id)
            item = dict(record_id=record_id, branch=branch, source_id=source_id,
                        title=row.get("title"), authors=row.get("authors"),
                        organization=row.get("organization"),
                        year=row.get("year"), type=row.get("type"),
                        language=row.get("language"), topics=row.get("topics"),
                        canonical_url=row.get("canonical_url"),
                        metadata_url=row.get("metadata_url"), doi=row.get("doi"),
                        isbn=row.get("isbn"), read_status=row.get("read_status"),
                        access_status=row.get("access_status"),
                        source_record_file=str(source.relative_to(ROOT)),
                        source_record_line=lineno,
                        review_group_key=group_key(row, record_id))
            for key in ["title", "read_status"]:
                if not item.get(key):
                    errors.append(f"{record_id}: missing {key}")
            locator = item.get("canonical_url") or item.get("metadata_url")
            if not isinstance(locator, str) or not locator.startswith(("https://", "http://")):
                errors.append(f"{record_id}: missing valid source URL")
            elif not item.get("canonical_url"):
                warnings.append(f"{record_id}: original publication URL pending; metadata_url is an evidence locator, not a substitute publication")
            records.append(item)
            branch_rows.append(item)
        counts[branch] = dict(records=len(branch_rows),
                             reading_status=dict(collections.Counter(r["read_status"] for r in branch_rows)),
                             source_types=dict(collections.Counter(r["type"] or "unspecified" for r in branch_rows)))
    groups = collections.defaultdict(list)
    for record in records:
        groups[record["review_group_key"]].append(record["record_id"])
    duplicates = [{"key": key, "records": value, "status": "review_linkage_not_silent_merge"}
                  for key, value in groups.items() if len(value) > 1]
    (BASE / "catalog.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    (BASE / "overlap-groups.json").write_text(json.dumps(duplicates, ensure_ascii=False, indent=2) + "\n")
    summary = dict(work_date="2026-10-20", records=len(records),
                   identifier_groups=len(groups), overlap_groups=len(duplicates),
                   counting_note="Records are not independent studies; groups need edition/version review. Full reading may describe a guide rather than a study.",
                   by_branch=counts, pending_branch_files=pending, warnings=warnings, errors=errors)
    (BASE / "catalog-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
