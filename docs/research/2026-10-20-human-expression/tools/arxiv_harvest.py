#!/usr/bin/env python3
"""Harvest arXiv preprints for the Chinese-expression evidence base.

arXiv covers the computational side of the question (readability, text
simplification, machine-generated text detection, translationese, discourse
parsing); it does not cover Chinese journal scholarship. Only records whose
PDF actually downloads and starts with the PDF magic bytes are written.

Usage:
    python3 arxiv_harvest.py --dry-run
    python3 arxiv_harvest.py --download
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "acquisition" / "round8"
PAPERS = Path(__file__).resolve().parents[4] / "papers" / "human-expression" / "round8"
ATOM = "{http://www.w3.org/2005/Atom}"

QUERIES = {
    "a01": 'all:"Chinese text simplification"',
    "a02": 'all:"Chinese readability"',
    "a03": 'all:"machine-generated text detection" AND all:Chinese',
    "a04": 'all:"AI-generated text detection"',
    "a05": 'all:"human vs machine text" AND all:stylistic',
    "a06": 'all:translationese',
    "a07": 'all:"discourse coherence" AND all:Chinese',
    "a08": 'all:"Chinese essay scoring"',
    "a09": 'all:"punctuation" AND all:"Chinese"',
    "a10": 'all:"sentence simplification" AND all:"Chinese"',
    "a11": 'all:"register" AND all:"variation" AND all:"corpus"',
    "a12": 'all:"metadiscourse"',
    "a13": 'all:"burstiness" AND all:"perplexity"',
    "a14": 'all:"style transfer" AND all:"text"',
    "a15": 'all:"grammatical error correction" AND all:Chinese',
    "a16": 'all:"discourse parsing" AND all:Chinese',
    "a17": 'all:"nominalization"',
    "a18": 'all:"readability assessment" AND all:Chinese',
    "a19": 'all:"LLM-generated text" AND all:detection',
    "a20": 'all:"watermark" AND all:"text generation"',
}

QUERIES_B = {
    "b01": 'all:"authorship attribution"',
    "b02": 'all:"stylometry"',
    "b03": 'all:"human-likeness" AND all:"text"',
    "b04": 'all:"paragraph" AND all:"coherence" AND all:"generation"',
    "b05": 'all:"zero anaphora" AND all:"Chinese"',
    "b06": 'all:"topic chain" AND all:Chinese',
    "b07": 'all:"sentence boundary detection"',
    "b08": 'all:"text rewriting" AND all:"style"',
    "b09": 'all:"paraphrase" AND all:"human"',
    "b10": 'all:"lexical diversity" AND all:"text"',
    "b11": 'all:"syntactic complexity"',
    "b12": 'all:"Chinese" AND all:"corpus" AND all:"written"',
    "b13": 'all:"simplification" AND all:"evaluation"',
    "b14": 'all:"readability" AND all:"formula"',
    "b15": 'all:"discourse relations" AND all:"Chinese"',
    "b16": 'all:"rhetorical structure" AND all:"Chinese"',
    "b17": 'all:"language model" AND all:"writing quality"',
    "b18": 'all:"revision" AND all:"writing" AND all:"model"',
    "b19": 'all:"informational" AND all:"narrative" AND all:"style"',
    "b20": 'all:"translation" AND all:"style" AND all:"corpus"',
}

HEADERS = {"User-Agent": "renhua-research/1.0 (evidence-base harvest)"}


def fetch(url: str, timeout: int = 40) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def existing_titles() -> set[str]:
    seen = set()
    for name in ("catalog.jsonl",):
        path = BASE / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            seen.add(re.sub(r"[^a-z0-9]+", "", str(record.get("title", "")).lower()))
    return seen


def search(query: str, limit: int = 25) -> list[dict]:
    url = (
        "https://export.arxiv.org/api/query?search_query="
        + urllib.parse.quote(query)
        + f"&start=0&max_results={limit}&sortBy=relevance"
    )
    root = ET.fromstring(fetch(url, timeout=60))
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        pdf = None
        for link in entry.findall(f"{ATOM}link"):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf = link.get("href")
        if not pdf:
            continue
        out.append(
            {
                "id": normalise(entry.findtext(f"{ATOM}id", "")),
                "title": normalise(entry.findtext(f"{ATOM}title", "")),
                "summary": normalise(entry.findtext(f"{ATOM}summary", "")),
                "published": normalise(entry.findtext(f"{ATOM}published", "")),
                "authors": [
                    normalise(a.findtext(f"{ATOM}name", ""))
                    for a in entry.findall(f"{ATOM}author")
                ],
                "pdf": pdf,
            }
        )
    return out


def slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text)[:80].strip("-")


def run(dry_run: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PAPERS.mkdir(parents=True, exist_ok=True)
    seen = existing_titles()
    candidates: list[dict] = []
    for qid, query in QUERIES.items():
        try:
            hits = search(query)
        except Exception as exc:  # noqa: BLE001 - network failures must not abort the sweep
            print(f"{qid} ERROR {exc}", flush=True)
            time.sleep(4)
            continue
        kept = 0
        for hit in hits:
            key = re.sub(r"[^a-z0-9]+", "", hit["title"].lower())
            if not key or key in seen:
                continue
            seen.add(key)
            hit["qid"] = qid
            candidates.append(hit)
            kept += 1
        print(f"{qid} kept={kept} hits={len(hits)}", flush=True)
        time.sleep(3.5)

    (OUT / "arxiv-candidates.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n"
    )
    print(f"candidates {len(candidates)}")
    if dry_run:
        return

    with (OUT / "arxiv-receipts.jsonl").open("w") as handle:
        for index, candidate in enumerate(candidates, 1):
            folder = PAPERS / f"{candidate['qid']}-{slugify(candidate['id'].rsplit('/', 1)[-1])}"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / "paper.pdf"
            receipt = {
                "qid": candidate["qid"],
                "title": candidate["title"],
                "authors": candidate["authors"],
                "year": int(candidate["published"][:4]) if candidate["published"][:4].isdigit() else None,
                "type": "preprint",
                "language": "en",
                "arxiv_id": candidate["id"],
                "url": candidate["id"],
                "path": str(target),
                "branch": "linguistics-intl",
                "abstract": candidate["summary"][:3000],
            }
            try:
                data = fetch(candidate["pdf"], timeout=90)
                if not data.startswith(b"%PDF-"):
                    receipt["result"] = "not_pdf"
                    handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                    continue
                target.write_bytes(data)
                from pypdf import PdfReader

                pages = len(PdfReader(str(target)).pages)
                receipt.update(
                    result="downloaded",
                    pages=pages,
                    bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                )
                print(f"[{index}/{len(candidates)}] {pages}p {candidate['title'][:60]}", flush=True)
            except Exception as exc:  # noqa: BLE001
                receipt.update(result="failed", error=str(exc)[:200])
                print(f"[{index}/{len(candidates)}] failed {candidate['title'][:50]}", flush=True)
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            time.sleep(2.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--set", default="a", choices=["a", "b"])
    args = parser.parse_args()
    if args.set == "b":
        QUERIES.clear()
        QUERIES.update(QUERIES_B)
    run(dry_run=not args.download)
