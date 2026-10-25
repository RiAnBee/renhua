#!/usr/bin/env python3
"""Register a specifically selected downloaded PDF; never scans browser storage.

Run with the bundled Python that provides pypdf. Metadata is a JSON file with
id, title, authors, year, canonical_url and optional bibliographic fields.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from pypdf import PdfReader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--metadata", required=True, type=Path)
    ap.add_argument("--destination", required=True, type=Path)
    ap.add_argument("--ledger", required=True, type=Path)
    args = ap.parse_args()
    metadata = json.loads(args.metadata.read_text())
    data = args.source.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise ValueError("Selected file is not a PDF")
    source_reader = PdfReader(args.source)
    if len(source_reader.pages) == 0:
        raise ValueError("PDF has no pages")
    digest = hashlib.sha256(data).hexdigest()
    target = args.destination / "paper.pdf"
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise ValueError("Destination contains a different file; preserve both versions")
    args.destination.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(args.source, target)
    reader = PdfReader(target)
    extractor = "pypdf"
    extraction_warning = None
    try:
        extracted = "\n\f\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        extraction_warning = f"pypdf: {type(exc).__name__}: {exc}"
        # Some older Chinese PDFs have broken CMaps. Keep the PDF and record
        # the failure even when a second extractor is unavailable.
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(target)
            extracted = "\n\f\n".join(page.get_textpage().get_text_range() for page in doc)
            extractor = "pdfium"
        except Exception as fallback_exc:
            extracted = ""
            extractor = "failed"
            extraction_warning += f"; pdfium: {type(fallback_exc).__name__}: {fallback_exc}"
    (args.destination / "text.txt").write_text(extracted)
    metadata.update(file=str(target), bytes=len(data), sha256=digest,
                    page_count=len(reader.pages), pdf_magic="%PDF-",
                    read_status="downloaded_not_yet_full_read",
                    extractor=extractor, extraction_warning=extraction_warning,
                    text_chars=len(extracted),
                    extraction_quality_flag="contains_nulls" if "\x00" in extracted
                    else "empty" if not extracted else "not_manually_checked")
    (args.destination / "receipt.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    existing = [json.loads(line) for line in args.ledger.read_text().splitlines()
                if line.strip()] if args.ledger.exists() else []
    matches = [row for row in existing if row["id"] == metadata["id"]]
    if matches and any(row.get("sha256") != digest for row in matches):
        raise ValueError("Ledger has a different version; resolve explicitly")
    if not matches:
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        with args.ledger.open("a") as stream:
            stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")
    print(json.dumps({key: metadata[key] for key in
                      ["id", "title", "file", "bytes", "page_count", "sha256"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
