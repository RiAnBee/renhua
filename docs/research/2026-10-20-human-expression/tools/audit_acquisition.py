#!/usr/bin/env python3
"""Audit the new research PDF collection; run with the bundled pypdf Python.

Only papers/human-expression is read. Legacy cloud PDFs are not hydrated.
Source records are linked rather than counted as independent publications.
"""
import collections
import hashlib
import json
import logging
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/research/2026-10-20-human-expression"


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def main():
    source_rows = []
    for branch in ("linguistics-zh", "linguistics-intl", "reading-cognition",
                   "practice-guides", "open-books", "citation-audits", "supplements"):
        path = BASE / branch / "sources.jsonl"
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    source_rows.append((branch, json.loads(line)))
    associations = collections.defaultdict(list)
    for branch, row in source_rows:
        for value in set(strings(row)):
            path = Path(value)
            if value.startswith("papers/human-expression/"):
                path = ROOT / value
            elif not path.is_absolute():
                continue
            if path.suffix.lower() == ".pdf" and path.is_relative_to(ROOT / "papers/human-expression"):
                associations[str(path.relative_to(ROOT))].append(branch + ":" + row["id"])
    records, errors = [], []
    for path in sorted((ROOT / "papers/human-expression").rglob("*.pdf")):
        rel = str(path.relative_to(ROOT))
        data = path.read_bytes()
        item = {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "collection": path.relative_to(ROOT / "papers/human-expression").parts[0],
                "source_records": sorted(set(associations.get(rel, []))),
                "reading_note": "file verification only; source card defines reading scope"}
        try:
            if not data.startswith(b"%PDF-"):
                raise ValueError("not PDF magic")
            parser_messages = []
            class CaptureWarnings(logging.Handler):
                def emit(self, record):
                    parser_messages.append(record.getMessage())
            handler = CaptureWarnings()
            logger = logging.getLogger("pypdf")
            logger.addHandler(handler)
            try:
                reader = PdfReader(path)
                item.update(pages=len(reader.pages), magic="%PDF-", encrypted=reader.is_encrypted)
            finally:
                logger.removeHandler(handler)
            item["parser_warnings"] = parser_messages
            if item["pages"] < 1:
                raise ValueError("zero pages")
        except Exception as exc:
            item["error"] = str(exc)
            errors.append(rel + ": " + str(exc))
        records.append(item)
    groups = collections.defaultdict(list)
    for row in records:
        groups[row["sha256"]].append(row["path"])
    summary = {"date": "2026-10-20", "pdf_files": len(records),
               "unique_file_hashes": len(groups), "bytes": sum(row["bytes"] for row in records),
               "pages": sum(row.get("pages", 0) for row in records),
               "by_collection": dict(collections.Counter(row["collection"] for row in records)),
               "duplicate_hash_groups": [value for value in groups.values() if len(value) > 1],
               "unlinked_files": [row["path"] for row in records if not row["source_records"]],
               "files_with_parser_warnings": [row["path"] for row in records if row.get("parser_warnings")],
               "errors": errors,
               "counting_note": "Includes articles, complete books, samples, handouts and frontmatter. Not full-reading or independent-study counts."}
    destination = BASE / "acquisition"
    destination.mkdir(exist_ok=True)
    (destination / "pdf-files.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    (destination / "pdf-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
