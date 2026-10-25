#!/usr/bin/env python3
"""Extract text layers from every registered PDF for systematic digestion.

Output: .harness/research-20261020/digest/text/<record-id>.txt
        .harness/research-20261020/digest/text-manifest.jsonl

The manifest records pages, characters, CJK ratio and a quality class so later
reading steps know whether a file is machine-readable, scanned, or broken.
Extraction never modifies the original PDF and never writes into docs/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RES = ROOT / "docs" / "research" / "2026-10-20-human-expression"
DIGEST = ROOT / ".harness" / "research-20261020" / "digest"
TEXT_DIR = DIGEST / "text"
BRANCHES = [
    "linguistics-zh", "linguistics-intl", "practice-guides", "open-books",
    "reading-cognition", "supplements", "citation-audits",
]

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")


def records() -> list[dict]:
    out = []
    for b in BRANCHES:
        p = RES / b / "sources.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            raw = r.get("files") or []
            paths = []
            for f in raw:
                if isinstance(f, str):
                    paths.append(f)
                elif isinstance(f, dict):
                    paths.append(f.get("file") or f.get("path") or (f.get("files") or [None])[0])
            pdfs = [p for p in paths if p and str(p).lower().endswith(".pdf")]
            if not pdfs:
                continue
            p0 = Path(pdfs[0])
            if not p0.exists():
                p0 = ROOT / pdfs[0]
            out.append({"id": r["id"], "branch": b, "pdf": str(p0.resolve())})
    # de-duplicate identical paths, keep first record id
    seen: dict[str, str] = {}
    uniq = []
    for rec in out:
        if rec["pdf"] in seen:
            continue
        seen[rec["pdf"]] = rec["id"]
        uniq.append(rec)
    return uniq


def extract(rec: dict) -> dict:
    from pypdf import PdfReader

    path = Path(rec["pdf"])
    if not path.exists():
        path = ROOT / rec["pdf"]
    entry = {"id": rec["id"], "branch": rec["branch"], "pdf": rec["pdf"], "pages": None,
             "chars": 0, "cjk_chars": 0, "latin_chars": 0, "quality": "error", "error": None,
             "text_file": None}
    try:
        reader = PdfReader(str(path))
        entry["pages"] = len(reader.pages)
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                chunks.append("")
        text = "\n\n".join(chunks)
        if reader.is_encrypted:
            entry["encrypted"] = True
        entry["chars"] = len(text)
        entry["cjk_chars"] = len(CJK.findall(text))
        entry["latin_chars"] = len(LATIN.findall(text))
        out = TEXT_DIR / f"{rec['id'].replace(':', '_')}.txt"
        if text.strip():
            out.write_text(text)
            entry["text_file"] = str(out.relative_to(ROOT))
        per_page = entry["chars"] / entry["pages"] if entry["pages"] else 0
        if not text.strip():
            entry["quality"] = "no_text_layer"
        elif per_page < 200:
            entry["quality"] = "sparse_text"
        elif entry["cjk_chars"] == 0 and entry["latin_chars"] > 0:
            entry["quality"] = "latin_only"
        else:
            entry["quality"] = "readable"
    except Exception as e:  # noqa: BLE001 - record the real failure per file
        entry["error"] = f"{type(e).__name__}: {e}"[:200]
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    recs = records()
    if args.limit:
        recs = recs[: args.limit]
    print(f"{len(recs)} distinct PDFs", file=sys.stderr)
    with ProcessPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(extract, recs))
    manifest = DIGEST / "text-manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n")
    stats: dict[str, int] = {}
    for e in entries:
        stats[e["quality"]] = stats.get(e["quality"], 0) + 1
    print(json.dumps({"files": len(entries), "pages": sum(e["pages"] or 0 for e in entries),
                      "chars": sum(e["chars"] for e in entries), "quality": stats},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
