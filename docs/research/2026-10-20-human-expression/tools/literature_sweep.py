#!/usr/bin/env python3
"""Systematic open-access literature sweep for the renhua research corpus.

Queries are fixed here, not invented per run, so the sweep is reproducible and
its coverage can be audited. Each query asks OpenAlex for works, keeps only
open-access records with a direct PDF URL, drops anything already in the
catalog, and (unless --dry-run) downloads and verifies the PDF.

  literature_sweep.py --dry-run            # candidate counts per query
  literature_sweep.py --download           # fetch PDFs into papers/.../round7

Outputs (under docs/research/2026-10-20-human-expression/acquisition/round7/):
  sweep-candidates.jsonl   one line per kept work, with the query that found it
  sweep-receipts.jsonl     download attempts and verification results
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
UA = "renhua-research/1.0 (systematic literature sweep)"
TIMEOUT = 30

# qid, branch, OpenAlex `title_and_abstract.search` terms (AND semantics),
# why this query exists. OpenAlex indexes almost no Chinese-language journals
# (tested: 语体/篇章/可读性 return 0–1 works), so Chinese-language acquisition
# cannot run through this sweep; these queries target English-language work,
# including English-language research on Chinese where it exists.
QUERIES = [
    ("q01", "linguistics-intl", "register variation multidimensional analysis",
     "语域多维分析框架"),
    ("q02", "linguistics-intl", "register genre style corpus linguistic variation",
     "语域/体裁/风格的关系"),
    ("q03", "linguistics-intl", "spoken written language differences corpus",
     "书面语与口语差异"),
    ("q04", "linguistics-intl", "Mandarin Chinese register variation",
     "汉语语域变异的英文研究"),
    ("q05", "linguistics-intl", "Chinese discourse cohesion anaphora",
     "汉语篇章衔接与回指"),
    ("q06", "linguistics-intl", "information structure topic focus Mandarin",
     "汉语信息结构"),
    ("q07", "linguistics-intl", "metadiscourse academic writing",
     "元话语"),
    ("q08", "linguistics-intl", "stance academic writing hedging",
     "立场与缓和"),
    ("q09", "linguistics-intl", "authorial voice academic writing",
     "作者声音"),
    ("q10", "linguistics-intl", "Chinese academic writing rhetorical",
     "中文学术语篇修辞"),
    ("q11", "linguistics-intl", "translationese translation universals",
     "翻译共性/翻译腔"),
    ("q12", "linguistics-intl", "Chinese Europeanized grammar translation",
     "汉语欧化与翻译"),
    ("q13", "linguistics-intl", "human machine generated text linguistic features",
     "人机文本的语言学差异"),
    ("q14", "linguistics-intl", "sentence length variation genre burstiness",
     "句长变化与体裁"),
    ("q15", "linguistics-intl", "revision writing quality feedback",
     "修改与写作质量"),
    ("q16", "linguistics-intl", "cohesion coherence text comprehension",
     "衔接连贯与理解"),
    ("q17", "linguistics-intl", "readability assessment text simplification",
     "可读性与简化"),
    ("q18", "linguistics-intl", "genre analysis move structure academic",
     "体裁与语步"),
    ("q19", "linguistics-intl", "punctuation prosody reading",
     "标点与韵律"),
    ("q20", "linguistics-intl", "writing process revision expertise",
     "写作过程中的修改"),
    ("q21", "linguistics-intl", "rater reliability writing assessment",
     "人工评分一致性"),
    ("q22", "linguistics-intl", "politeness Chinese interaction pragmatics",
     "汉语礼貌与互动"),
    ("q23", "linguistics-intl", "parallelism repetition rhetoric effect",
     "排比/重复的表达功能"),
    ("q24", "linguistics-intl", "plain language editing intervention",
     "简明语言与编辑干预"),
    ("q25", "linguistics-intl", "discourse marker function conversation",
     "话语标记功能"),
    ("q26", "linguistics-intl", "nominalization complexity academic register",
     "名词化与学术语域"),
    ("q27", "reading-cognition", "sentence processing Chinese reading",
     "汉语句子加工"),
    ("q28", "reading-cognition", "reading time predictability Chinese",
     "可预测性与阅读时间"),
    ("q29", "reading-cognition", "coherence inference text comprehension experiment",
     "连贯推理实验"),
]

MIN_PAGES = 3
MAX_PER_QUERY = 8


def http_json(url, tries=5):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read()), None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, "http 404"
            last = f"http {exc.code}"
            if exc.code == 429:
                time.sleep(8 * (attempt + 1))
                continue
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)
        time.sleep(2.5 * (attempt + 1))
    return None, last


def invert(index):
    if not isinstance(index, dict):
        return ""
    pairs = []
    for word, positions in index.items():
        for position in positions or []:
            pairs.append((position, word))
    return " ".join(word for _, word in sorted(pairs))


def load_catalog():
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


def already_present(work, titles, dois):
    doi = (work.get("doi") or "").replace("https://doi.org/", "").lower()
    if doi and doi in dois:
        return "doi"
    key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (work.get("title") or "").lower())
    if key and key in titles:
        return "title"
    return None


def run(dry_run, only=None, max_per_query=MAX_PER_QUERY):
    titles, dois = load_catalog()
    seen = set()
    candidates = []
    OUT.mkdir(parents=True, exist_ok=True)
    for qid, branch, query, why in QUERIES:
        if only and qid not in only:
            continue
        filters = ("is_oa:true,from_publication_date:1980-01-01,type:article|book-chapter|review|book"
                   ",title_and_abstract.search:" + query)
        url = ("https://api.openalex.org/works?per-page=25&filter="
               + urllib.parse.quote(filters, safe=":,"))
        data, error = http_json(url)
        if error:
            print(f"{qid} ERROR {error}", flush=True)
            continue
        kept = 0
        for work in (data or {}).get("results") or []:
            if kept >= max_per_query:
                break
            pdf = ((work.get("best_oa_location") or {}).get("pdf_url")
                   or next(((loc.get("pdf_url")) for loc in work.get("locations") or []
                            if loc.get("is_oa") and loc.get("pdf_url")), None))
            if not pdf:
                continue
            duplicate = already_present(work, titles, dois)
            if duplicate:
                continue
            doi = (work.get("doi") or "").replace("https://doi.org/", "")
            key = doi or re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (work.get("title") or "").lower())
            if key in seen:
                continue
            seen.add(key)
            authors = [a["author"]["display_name"] for a in work.get("authorships") or []
                       if a.get("author", {}).get("display_name")]
            candidates.append({
                "qid": qid, "branch": branch, "query": query, "why": why,
                "openalex_id": work.get("id"), "doi": doi or None,
                "title": work.get("title"), "authors": authors,
                "year": work.get("publication_year"), "type": work.get("type"),
                "language": work.get("language") or "en",
                "cited_by_count": work.get("cited_by_count"),
                "open_access": work.get("open_access"),
                "pdf_url": pdf,
                "landing_page_url": (work.get("primary_location") or {}).get("landing_page_url"),
                "abstract": invert(work.get("abstract_inverted_index"))[:4000],
            })
            kept += 1
        print(f"{qid} kept={kept} total={len(candidates)}", flush=True)
        time.sleep(3.0)

    (OUT / "sweep-candidates.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n")
    print(f"candidates {len(candidates)} -> {OUT/'sweep-candidates.jsonl'}")
    if dry_run:
        return

    from pypdf import PdfReader
    with (OUT / "sweep-receipts.jsonl").open("w") as handle:
        for index, candidate in enumerate(candidates, 1):
            slug = re.sub(r"[^A-Za-z0-9._-]+", "-", (candidate["doi"] or candidate["title"])[:60]).strip("-")
            folder = ROOT / "papers/human-expression/round7" / f"{candidate['qid']}-{slug}"
            target = folder / "paper.pdf"
            receipt = {**candidate, "path": str(target.relative_to(ROOT))}
            if target.exists() and target.read_bytes().startswith(b"%PDF-"):
                receipt.update(result="already_present")
            else:
                try:
                    request = urllib.request.Request(candidate["pdf_url"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(request, timeout=60) as response:
                        body = response.read()
                except Exception as exc:  # noqa: BLE001
                    receipt.update(result="failed", error=repr(exc)[:200])
                    handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                    print(f"[{index}/{len(candidates)}] FAIL {candidate['title'][:50]}", flush=True)
                    continue
                if not body.startswith(b"%PDF-") or len(body) < 40000:
                    receipt.update(result="failed", error=f"not a pdf ({len(body)} bytes)")
                    handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                    continue
                folder.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                pages = 0
                try:
                    pages = len(PdfReader(target).pages)
                except Exception as exc:  # noqa: BLE001
                    receipt.setdefault("parser_warning", repr(exc)[:200])
                if pages < MIN_PAGES:
                    target.unlink()
                    receipt.update(result="failed", error=f"pages {pages} < {MIN_PAGES}")
                    handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
                    continue
                receipt.update(result="downloaded", bytes=len(body), pages=pages,
                               sha256=hashlib.sha256(body).hexdigest())
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"[{index}/{len(candidates)}] {receipt['result']:<16} {receipt.get('pages','')}p {candidate['title'][:50]}", flush=True)
            time.sleep(0.3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--query", nargs="*")
    parser.add_argument("--max-per-query", type=int, default=MAX_PER_QUERY)
    args = parser.parse_args()
    run(dry_run=not args.download, only=set(args.query) if args.query else None,
        max_per_query=args.max_per_query)


if __name__ == "__main__":
    main()
