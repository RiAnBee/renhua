#!/usr/bin/env python3
"""Probe open-access routes for research records and, optionally, download them.

Standard library only. Two stages are deliberately separate so a probe never
implies a file was obtained:

  probe  items.jsonl   -> receipts.jsonl   (routes, matches, candidate PDF URLs)
  fetch  receipts.jsonl-> papers/... + fetch-receipts.jsonl

Routes, in order: OpenAlex (by DOI, else title search), Semantic Scholar
openAccessPdf, arXiv title search, OAPEN/DOAB (books), Internet Archive
(unrestricted texts only). Every attempt is recorded; nothing is inferred.

Run from the renhua repository root:

  python3 docs/research/2026-10-20-human-expression/tools/oa_acquire.py \
      probe --input docs/research/2026-10-20-human-expression/acquisition/round7/items.jsonl \
            --out   docs/research/2026-10-20-human-expression/acquisition/round7/probe-receipts.jsonl
"""
import argparse
import difflib
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
UA = "renhua-research/1.0 (literature acquisition; contact via repository issue)"
TIMEOUT = 30
SLEEP = 0.35


def http(url, headers=None, tries=3):
    request = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.status, response.read(), response.geturl()
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 403, 401, 400):
                return exc.code, b"", url
            last = exc
        except Exception as exc:  # noqa: BLE001 - network errors vary by host
            last = exc
        time.sleep(1.2 * (attempt + 1))
    return None, repr(last).encode(), url


def http_json(url):
    status, body, final = http(url)
    if status != 200:
        return None, f"http {status}: {body[:120]!r}"
    try:
        return json.loads(body), None
    except json.JSONDecodeError as exc:
        return None, f"bad json: {exc}"


def norm(text):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (text or "").lower()).strip()


def similarity(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def work_locations(work):
    urls = []
    seen = set()

    def add(url, kind, note):
        if not isinstance(url, str) or not url.startswith("http"):
            return
        if url in seen:
            return
        seen.add(url)
        urls.append({"url": url, "kind": kind, "note": note})

    best = work.get("best_oa_location") or {}
    if best.get("pdf_url"):
        add(best["pdf_url"], "pdf", "openalex:best_oa_location")
    for location in work.get("locations") or []:
        if not location.get("is_oa"):
            continue
        if location.get("pdf_url"):
            add(location["pdf_url"], "pdf", "openalex:location")
        if location.get("landing_page_url"):
            add(location["landing_page_url"], "landing", "openalex:location")
    oa = work.get("open_access") or {}
    if oa.get("oa_url"):
        add(oa["oa_url"], "landing", "openalex:open_access.oa_url")
    return urls


def openalex_by_doi(doi, attempts):
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi.strip())
    work, err = http_json("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi))
    attempts.append({"route": "openalex_doi", "query": doi, "error": err})
    return work if isinstance(work, dict) and work.get("id") else None


def openalex_search(item, attempts):
    query = item["title"]
    if item.get("authors"):
        query += " " + item["authors"][0].split()[-1]
    url = ("https://api.openalex.org/works?per-page=5&search="
           + urllib.parse.quote(query))
    data, err = http_json(url)
    attempts.append({"route": "openalex_search", "query": query, "error": err})
    best, best_score = None, 0.0
    for work in (data or {}).get("results") or []:
        score = similarity(item["title"], work.get("title"))
        if item.get("year") and work.get("publication_year"):
            if abs(int(work["publication_year"]) - int(item["year"])) <= 2:
                score += 0.05
        if score > best_score:
            best, best_score = work, score
    if best is not None and best_score >= 0.86:
        return best, round(best_score, 3)
    return None, round(best_score, 3)


def semantic_scholar(doi, attempts):
    url = ("https://api.semanticscholar.org/graph/v1/paper/DOI:"
           + urllib.parse.quote(re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi))
           + "?fields=title,openAccessPdf,isOpenAccess,year")
    data, err = http_json(url)
    attempts.append({"route": "semantic_scholar", "query": doi, "error": err})
    return data if isinstance(data, dict) else None


def arxiv(item, attempts):
    query = 'ti:"%s"' % item["title"].replace('"', "")
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(query)
           + "&max_results=3")
    status, body, _ = http(url)
    attempts.append({"route": "arxiv", "query": query, "error": None if status == 200 else f"http {status}"})
    if status != 200:
        return []
    text = body.decode("utf-8", "ignore")
    out = []
    for entry in text.split("<entry>")[1:]:
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        if title is None:
            continue
        title = re.sub(r"\s+", " ", title.group(1)).strip()
        if similarity(title, item["title"]) < 0.86:
            continue
        pdf = re.search(r'<link[^>]*title="pdf"[^>]*href="([^"]+)"', entry)
        if pdf:
            out.append({"url": pdf.group(1), "kind": "pdf", "note": f"arxiv:{title[:80]}"})
    return out


def oapen_doab(item, attempts):
    out = []
    for base in ("https://library.oapen.org", "https://directory.doabooks.org"):
        url = base + "/rest/search?query=" + urllib.parse.quote(item["title"]) + "&expand=metadata,bitstreams"
        data, err = http_json(url)
        attempts.append({"route": base.split("//")[1].split("/")[0], "query": item["title"], "error": err})
        for record in (data or []) if isinstance(data, list) else []:
            for stream in record.get("bitstreams") or []:
                name = (stream.get("name") or "").lower()
                link = stream.get("retrieveLink")
                if link and (name.endswith(".pdf") or stream.get("mimeType") == "application/pdf"):
                    out.append({"url": base + link, "kind": "pdf", "note": base.split("//")[1].split("/")[0]})
    return out


def internet_archive(item, attempts):
    query = 'title:(%s) AND mediatype:texts' % re.sub(r"[^A-Za-z0-9 ]+", " ", item["title"]).strip()
    url = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(query)
           + "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=access-restricted-item"
             "&rows=5&page=1&output=json")
    data, err = http_json(url)
    attempts.append({"route": "internet_archive", "query": query, "error": err})
    out = []
    docs = ((data or {}).get("response") or {}).get("docs") or []
    for doc in docs:
        if str(doc.get("access-restricted-item")).lower() in ("true", "1"):
            continue
        if similarity(item["title"], doc.get("title")) < 0.8:
            continue
        ident = doc["identifier"]
        out.append({"url": f"https://archive.org/download/{ident}/{ident}.pdf",
                    "kind": "pdf", "note": f"internet_archive:{ident}"})
    return out


def probe_item(item):
    attempts, pdf_urls = [], []
    work = None
    if item.get("doi"):
        work = openalex_by_doi(item["doi"], attempts)
        score = 1.0
    else:
        work, score = openalex_search(item, attempts)
    if work:
        for entry in work_locations(work):
            (pdf_urls if entry["kind"] == "pdf" else attempts).append(entry)
    if not pdf_urls:
        if item.get("doi"):
            scholar = semantic_scholar(item["doi"], attempts)
            pdf = (scholar or {}).get("openAccessPdf") or {}
            if pdf.get("url"):
                pdf_urls.append({"url": pdf["url"], "kind": "pdf", "note": "semantic_scholar"})
    if not pdf_urls:
        pdf_urls.extend(arxiv(item, attempts))
    if not pdf_urls and item.get("type", "").lower() in {"book", "edited_book", "edited-book", "open_book", "chapter"}:
        pdf_urls.extend(oapen_doab(item, attempts))
        pdf_urls.extend(internet_archive(item, attempts))
    oa = (work or {}).get("open_access") or {}
    return {
        "id": item["id"],
        "title": item["title"],
        "doi": item.get("doi"),
        "type": item.get("type"),
        "year": item.get("year"),
        "openalex_id": (work or {}).get("id"),
        "match_score": score if work else None,
        "is_oa": bool(pdf_urls) or bool(oa.get("is_oa")),
        "oa_status": oa.get("oa_status"),
        "landing_pages": [a for a in attempts if isinstance(a, dict) and a.get("kind") == "landing"],
        "pdf_candidates": pdf_urls,
        "attempts": [a for a in attempts if not (isinstance(a, dict) and a.get("kind"))],
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def download(url, destination):
    headers = {"Accept": "application/pdf,*/*"}
    status, body, final = http(url, headers=headers, tries=2)
    if status != 200:
        return None, f"http {status}"
    if not body.startswith(b"%PDF-"):
        return None, f"not pdf magic ({body[:16]!r}, {len(body)} bytes) from {final}"
    if len(body) < 40000:
        return None, f"implausible size {len(body)} bytes"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)
    return destination, None


def summarise(destination):
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"pages": None, "note": "pypdf unavailable"}
    try:
        reader = PdfReader(destination)
        return {"pages": len(reader.pages), "encrypted": reader.is_encrypted}
    except Exception as exc:  # noqa: BLE001
        return {"pages": None, "note": f"{type(exc).__name__}: {exc}"}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--input", required=True, type=Path)
    p_probe.add_argument("--out", required=True, type=Path)
    p_probe.add_argument("--limit", type=int)
    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("--receipts", required=True, type=Path)
    p_fetch.add_argument("--dest", required=True, type=Path, help="directory root for per-record folders")
    p_fetch.add_argument("--out", required=True, type=Path)
    p_fetch.add_argument("--only", nargs="*", help="restrict to these record ids")
    args = parser.parse_args()

    if args.command == "probe":
        items = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
        if args.limit:
            items = items[: args.limit]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as handle, args.out.with_suffix(".log").open("w") as log:
            for index, item in enumerate(items, 1):
                receipt = probe_item(item)
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                handle.flush()
                line = (f"[{index}/{len(items)}] {item['id']:<44} "
                        f"oa={receipt['is_oa']!s:<5} pdfs={len(receipt['pdf_candidates'])} "
                        f"status={receipt['oa_status']}")
                print(line, flush=True)
                log.write(line + "\n")
                time.sleep(SLEEP)
        return

    receipts = [json.loads(line) for line in args.receipts.read_text().splitlines() if line.strip()]
    if args.only:
        receipts = [r for r in receipts if r["id"] in set(args.only)]
    dest_root = args.dest if args.dest.is_absolute() else ROOT / args.dest
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as handle:
        for receipt in receipts:
            if not receipt.get("pdf_candidates"):
                handle.write(json.dumps({**receipt, "fetch": {"result": "no_candidate"}}, ensure_ascii=False) + "\n")
                continue
            record_dir = dest_root / re.sub(r"[^A-Za-z0-9._-]+", "-", receipt["id"])
            target = record_dir / "paper.pdf"
            evidence, success = [], False
            if target.exists() and target.read_bytes().startswith(b"%PDF-"):
                success = True
                evidence.append({"url": None, "note": "already present", "sha256":
                                 hashlib.sha256(target.read_bytes()).hexdigest()})
            for candidate in receipt["pdf_candidates"]:
                if success:
                    break
                path, error = download(candidate["url"], target)
                evidence.append({"url": candidate["url"], "note": candidate.get("note"),
                                 "error": error,
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path else None})
                success = bool(path)
                time.sleep(SLEEP)
            result = {"result": "downloaded" if success else "failed", "evidence": evidence}
            if success:
                info = summarise(target)
                result.update(path=str(target.relative_to(ROOT)), bytes=target.stat().st_size, **info)
            handle.write(json.dumps({**receipt, "fetch": result}, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"{receipt['id']:<44} {result['result']:<11} "
                  f"{result.get('pages', '')}p {result.get('bytes', '')}B", flush=True)


if __name__ == "__main__":
    sys.exit(main())
