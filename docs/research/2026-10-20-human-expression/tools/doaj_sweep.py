#!/usr/bin/env python3
"""DOAJ-based open-access sweep (used when OpenAlex rate-limits us).

DOAJ indexes open-access journals only, so every hit is lawfully downloadable.
Queries are title-level to keep precision; each hit is resolved to a PDF by
following the landing page when DOAJ gives no direct PDF link.

  doaj_sweep.py --dry-run
  doaj_sweep.py --download
"""
import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/research/2026-10-20-human-expression"
OUT = BASE / "acquisition/round7"
UA = "renhua-research/1.0 (DOAJ literature sweep)"
TIMEOUT = 40
MAX_PER_QUERY = 6
MIN_PAGES = 2

QUERIES = [
    ("d01", "linguistics-intl", 'bibjson.title:"register variation"', "语域变异"),
    ("d02", "linguistics-intl", 'bibjson.title:"register" AND bibjson.title:"Chinese"', "汉语语域"),
    ("d03", "linguistics-intl", 'bibjson.title:"cohesion" AND bibjson.title:"coherence"', "衔接与连贯"),
    ("d04", "linguistics-intl", 'bibjson.title:"metadiscourse"', "元话语"),
    ("d05", "linguistics-intl", 'bibjson.title:"stance" AND bibjson.title:"academic"', "学术立场"),
    ("d06", "linguistics-intl", 'bibjson.title:"hedging"', "缓和语"),
    ("d07", "linguistics-intl", 'bibjson.title:"authorial voice"', "作者声音"),
    ("d08", "linguistics-intl", 'bibjson.title:"translationese"', "翻译腔"),
    ("d09", "linguistics-intl", 'bibjson.title:"readability"', "可读性"),
    ("d10", "linguistics-intl", 'bibjson.title:"text simplification"', "文本简化"),
    ("d11", "linguistics-intl", 'bibjson.title:"genre analysis"', "体裁分析"),
    ("d12", "linguistics-intl", 'bibjson.title:"discourse marker"', "话语标记"),
    ("d13", "linguistics-intl", 'bibjson.title:"information structure"', "信息结构"),
    ("d14", "linguistics-intl", 'bibjson.title:"nominalization"', "名词化"),
    ("d15", "linguistics-intl", 'bibjson.title:"punctuation"', "标点"),
    ("d16", "linguistics-intl", 'bibjson.title:"revision" AND bibjson.title:"writing"', "修改与写作"),
    ("d17", "linguistics-intl", 'bibjson.title:"feedback" AND bibjson.title:"writing"', "反馈与写作"),
    ("d18", "linguistics-intl", 'bibjson.title:"Chinese" AND bibjson.title:"writing"', "汉语写作"),
    ("d19", "linguistics-intl", 'bibjson.title:"Mandarin"', "普通话研究"),
    ("d20", "linguistics-intl", 'bibjson.title:"politeness" AND bibjson.title:"Chinese"', "汉语礼貌"),
    ("d21", "linguistics-intl", 'bibjson.title:"rater" AND bibjson.title:"reliability"', "评分一致性"),
    ("d22", "linguistics-intl", 'bibjson.title:"plain language"', "简明语言"),
    ("d23", "linguistics-intl", 'bibjson.title:"academic writing"', "学术写作"),
    ("d24", "linguistics-intl", 'bibjson.title:"writer identity"', "写作者身份"),
    ("d25", "linguistics-intl", 'bibjson.title:"sentence complexity"', "句子复杂度"),
    ("d26", "linguistics-intl", 'bibjson.title:"translation" AND bibjson.title:"Chinese"', "汉语翻译研究"),
    ("d27", "reading-cognition", 'bibjson.title:"eye movements" AND bibjson.title:"Chinese"', "汉语眼动"),
    ("e01", "linguistics-intl", 'bibjson.title:"copyediting"', "编辑加工"),
    ("e02", "linguistics-intl", 'bibjson.title:"plain language"', "简明语言"),
    ("e03", "linguistics-intl", 'bibjson.title:"academic writing" AND bibjson.title:"Chinese"', "汉语学术写作"),
    ("e04", "linguistics-intl", 'bibjson.title:"writing quality"', "写作质量"),
    ("e05", "linguistics-intl", 'bibjson.title:"stylistic" AND bibjson.title:"corpus"', "语料库文体"),
    ("e06", "linguistics-intl", 'bibjson.title:"coherence" AND bibjson.title:"writing"', "写作连贯"),
    ("e07", "linguistics-intl", 'bibjson.title:"paragraph"', "段落组织"),
    ("e08", "linguistics-intl", 'bibjson.title:"sentence" AND bibjson.title:"complexity"', "句子复杂度"),
    ("e09", "linguistics-intl", 'bibjson.title:"translation" AND bibjson.title:"style"', "翻译风格"),
    ("e10", "linguistics-intl", 'bibjson.title:"AI-generated" AND bibjson.title:"text"', "AI 生成文本"),
    ("e11", "linguistics-intl", 'bibjson.title:"peer review" AND bibjson.title:"revision"', "审稿与修改"),
    ("e12", "linguistics-intl", 'bibjson.title:"second language writing"', "二语写作"),
    ("d28", "reading-cognition", 'bibjson.title:"reading comprehension" AND bibjson.title:"coherence"', "阅读理解与连贯"),
]


def fetch(url, headers=None, tries=3):
    request = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read(), response.geturl()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + attempt * 2)
    return None, repr(last)


def doaj(query, page_size=50):
    url = ("https://doaj.org/api/search/articles/" + urllib.parse.quote(query)
           + f"?pageSize={page_size}")
    body, _ = fetch(url)
    if body is None:
        return []
    try:
        return json.loads(body).get("results") or []
    except json.JSONDecodeError:
        return []


def pdf_link_from_html(url):
    body, final = fetch(url, headers={"Accept": "text/html"})
    if body is None:
        return None
    html = body.decode("utf-8", "ignore")
    match = re.search(r'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"', html, re.I)
    if not match:
        match = re.search(r'content="([^"]+\.pdf[^"]*)"[^>]+name="citation_pdf_url"', html, re.I)
    if match:
        return urllib.parse.urljoin(final, match.group(1))
    for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I):
        return urllib.parse.urljoin(final, href.replace("&amp;", "&"))
    # OJS / Open Journal Systems galley downloads carry no .pdf suffix
    for href in re.findall(r'href="([^"]*/article/download/[^"]+)"', html, re.I):
        return urllib.parse.urljoin(final, href.replace("&amp;", "&"))
    return None


def load_existing():
    titles, dois = set(), set()
    for line in (BASE / "catalog.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("title"):
            titles.add(re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", row["title"].lower()))
        if row.get("doi"):
            dois.add(row["doi"].lower())
    return titles, dois


def run(dry_run, only=None, input_path=None, receipts=None, papers_subdir='round7'):
    if input_path is not None:
        candidates = [json.loads(line) for line in input_path.read_text().splitlines() if line.strip()]
        download_candidates(candidates, receipts)
        return
    titles, dois = load_existing()
    seen, candidates = set(), []
    OUT.mkdir(parents=True, exist_ok=True)
    for qid, branch, query, why in QUERIES:
        if only and qid not in only:
            continue
        kept = 0
        for record in doaj(query):
            if kept >= MAX_PER_QUERY:
                break
            bib = record.get("bibjson") or {}
            title = (bib.get("title") or "").strip()
            if not title:
                continue
            doi = next((i.get("id") for i in bib.get("identifier") or []
                        if i.get("type") == "doi"), None)
            key = doi or re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())
            norm = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())
            if key in seen or (doi and doi.lower() in dois) or norm in titles:
                continue
            seen.add(key)
            links = bib.get("link") or []
            direct = [l["url"] for l in links
                      if (l.get("content_type") or "").lower().endswith("pdf") and l.get("url")]
            landing = [l["url"] for l in links
                       if (l.get("content_type") or "").lower() not in ("pdf",)
                       and l.get("url") and not l["url"].startswith("https://doi.org/")]
            candidates.append({
                "qid": qid, "branch": branch, "query": query, "why": why,
                "title": title, "doi": doi,
                "authors": [a.get("name") for a in bib.get("author") or [] if a.get("name")],
                "year": bib.get("year"), "type": "journal_article",
                "language": "en",
                "journal": (bib.get("journal") or {}).get("title"),
                "license": [l.get("type") for l in bib.get("license") or []],
                "pdf_urls": direct,
                "landing_pages": landing[:2],
                "abstract": re.sub(r"<[^>]+>", " ", bib.get("abstract") or "")[:3000],
            })
            kept += 1
        print(f"{qid} kept={kept} total={len(candidates)}", flush=True)
        time.sleep(1.0)

    (OUT / "doaj-candidates.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n")
    print(f"candidates {len(candidates)}")
    if dry_run:
        return

    download_candidates(candidates, papers_subdir=papers_subdir)


def candidate_pdf_variants(candidate, resolved):
    """Extra URL shapes for publishers whose PDF link is not exposed statically."""
    urls = list(resolved)
    for landing in candidate.get("landing_pages") or []:
        if landing.rstrip("/").endswith("/pdf"):
            continue
        urls.append(landing.rstrip("/") + "/pdf")            # MDPI / OJS style
        if "/article/view/" in landing:
            urls.append(landing.rstrip("/") + "/0")           # OJS default galley
        if "plos.org" in landing and "id=" in landing:
            base = landing.split("?")[0]
            urls.append(base + "/file?type=printable&id=" + landing.split("id=")[1].split("&")[0])
    return urls


def download_candidates(candidates, receipts_path=None, papers_subdir='round7'):
    from pypdf import PdfReader
    receipts_path = receipts_path or (OUT / "doaj-receipts.jsonl")
    with receipts_path.open("w") as handle:
        for index, candidate in enumerate(candidates, 1):
            slug = re.sub(r"[^A-Za-z0-9._-]+", "-", (candidate["doi"] or candidate["title"])[:60]).strip("-")
            folder = ROOT / "papers/human-expression" / papers_subdir / f"{candidate['qid']}-{slug}"
            target = folder / "paper.pdf"
            receipt = {**candidate, "path": str(target.relative_to(ROOT))}
            urls = list(candidate["pdf_urls"])
            for landing in candidate["landing_pages"]:
                resolved = pdf_link_from_html(landing)
                if resolved:
                    urls.append(resolved)
            urls = candidate_pdf_variants(candidate, urls)
            if not urls:
                receipt.update(result="failed", error="no pdf link resolved")
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                continue
            done = False
            for url in urls[:4]:
                body, final = fetch(url, headers={"Accept": "application/pdf"})
                if body is None or not body.startswith(b"%PDF-") or len(body) < 30000:
                    receipt.setdefault("tried", []).append({"url": url, "error": "not a usable pdf"})
                    continue
                folder.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                pages = 0
                try:
                    pages = len(PdfReader(target).pages)
                except Exception as exc:  # noqa: BLE001
                    receipt.setdefault("parser_warning", repr(exc)[:160])
                if pages < MIN_PAGES:
                    target.unlink()
                    receipt.setdefault("tried", []).append({"url": url, "error": f"pages {pages}"})
                    continue
                receipt.update(result="downloaded", source_url=url, bytes=len(body),
                               pages=pages, sha256=hashlib.sha256(body).hexdigest())
                done = True
                break
            if not done:
                receipt.update(result="failed", error="all urls rejected")
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"[{index}/{len(candidates)}] {receipt['result']:<11} {receipt.get('pages','')}p "
                  f"{candidate['title'][:55]}", flush=True)
            time.sleep(0.6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--query", nargs="*")
    parser.add_argument("--input", type=Path, help="curated candidate file for download mode")
    parser.add_argument("--out", type=Path, help="receipts file for download mode")
    parser.add_argument("--papers-subdir", default="round7", help="folder under papers/human-expression")
    args = parser.parse_args()
    run(dry_run=not args.download, only=set(args.query) if args.query else None,
        input_path=args.input, receipts=args.out, papers_subdir=args.papers_subdir)


if __name__ == "__main__":
    main()
