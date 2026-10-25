#!/usr/bin/env python3
"""Append verified round-7 downloads as source records.

Only files that were actually downloaded and parsed qualify. Records land in
the existing branch source files so that catalog, queues and validation keep
working unchanged. New records are honest about their state: `metadata` reading
status, no findings, an explicit acquisition receipt.

  register_round7.py --receipts acquisition/round7/sweep-receipts.jsonl --dry-run
  register_round7.py --receipts acquisition/round7/sweep-receipts.jsonl --apply

Also appends a line per record to acquisition/round7/merge-log.jsonl.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/research/2026-10-20-human-expression"
BRANCHES = ("linguistics-zh", "linguistics-intl", "reading-cognition")
TODAY = "2026-10-23"


def existing(path):
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def next_zh_id(rows):
    numbers = []
    for row in rows:
        match = re.match(r"ZH(\d+)", str(row.get("id")))
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) if numbers else 0) + 1


def author_slug(candidate):
    authors = candidate.get("authors") or []
    if authors:
        last = re.split(r"[ ,]+", authors[0].strip())[-1]
        last = re.sub(r"[^A-Za-z]", "", last) or "anon"
    else:
        last = "anon"
    year = candidate.get("year") or "nd"
    return f"{last.upper()}-{year}"


def build_record(candidate, branch, branch_rows, receipt_path, page_count, sha256,
                 byte_count, source_id):
    topics, _ = topics_for(candidate)
    doi = candidate.get("doi")
    url = ((f"https://doi.org/{doi}" if doi else None)
           or candidate.get("landing_page_url")
           or candidate.get("source_url")
           or candidate.get("pdf_url"))
    absolute = str((ROOT / receipt_path).resolve())
    return {
        "id": source_id,
        "title": candidate.get("title"),
        "authors": candidate.get("authors") or [],
        "year": candidate.get("year"),
        "type": candidate.get("type") or "journal_article",
        "language": candidate.get("language"),
        "topics": topics,
        "canonical_url": url,
        "doi": doi or None,
        "isbn": None,
        "read_status": "metadata",
        "access_status": "open_access_downloaded",
        "findings": None,
        "implications_and_limits": None,
        "files": [{
            "file": absolute,
            "bytes": byte_count,
            "sha256": sha256,
            "page_count": page_count,
            "document_extent": "full_article_pdf_unverified",
            "acquisition_receipt_id": f"round7-{candidate['qid']}",
            "source_id": branch + ":" + source_id,
            "format": "pdf",
            "full_book": False,
        }],
        "query_ids": [candidate["qid"]],
        "record_origin": "round7_openalex_sweep",
        "verified_at": TODAY,
        "version_notes": "Open-access copy located through OpenAlex; publisher version not yet compared.",
        "fulltext_obtained": True,
        "fulltext_format": "pdf",
        "complete_original_pdf": None,
        "read_sections": None,
    }


def topics_for(candidate):
    mapping = {
        "q01": ["语体", "书面口语差异"], "q02": ["语体语法", "正式度"],
        "q03": ["篇章", "衔接", "连贯"], "q04": ["信息结构", "语序"],
        "q05": ["指称", "回指"], "q06": ["修辞", "修改"], "q07": ["学术语篇", "立场"],
        "q08": ["公文", "新闻语体"], "q09": ["编辑", "修改"],
        "q10": ["翻译腔", "欧化"], "q11": ["标点", "断句", "韵律"],
        "q12": ["韵律", "句法"], "q13": ["可读性", "文本难度"],
        "q14": ["语料库", "多维分析"], "q15": ["网络语言", "新媒体"],
        "q16": ["句长", "句法复杂度"], "q17": ["语气词", "情态", "立场"],
        "q18": ["省略", "零形回指"],
        "q19": ["语域", "多维分析"], "q20": ["人机文本差异"],
        "q21": ["句长变化", "人类写作"], "q22": ["修改", "干预实验"],
        "q23": ["衔接", "理解"], "q24": ["元话语", "立场"],
        "q25": ["作者声音"], "q26": ["信息结构", "加工"],
        "q27": ["可读性", "文本简化"], "q28": ["翻译共性", "翻译腔"],
        "q29": ["体裁", "语步"], "q30": ["韵律", "标点", "句法"],
        "q31": ["写作过程", "修改"], "q32": ["评分", "人工评价"],
        "q33": ["语用", "礼貌"], "q34": ["对偶", "排比", "修辞"],
        "q35": ["语料库", "书面语域"], "q36": ["句子加工", "阅读"],
        "d01": ["语域变异"], "d02": ["汉语语域"], "d03": ["衔接", "连贯"],
        "d04": ["元话语"], "d05": ["学术立场"], "d06": ["缓和语"],
        "d07": ["作者声音"], "d08": ["翻译腔"], "d09": ["可读性"],
        "d10": ["文本简化"], "d11": ["体裁", "语步"], "d12": ["话语标记"],
        "d13": ["信息结构"], "d14": ["名词化"], "d15": ["标点"],
        "d16": ["修改", "写作"], "d17": ["反馈", "写作"], "d18": ["汉语写作"],
        "d19": ["普通话"], "d20": ["汉语礼貌"], "d21": ["评分一致性"],
        "d22": ["简明语言"], "d23": ["学术写作"], "d24": ["写作者身份"],
        "d25": ["句子复杂度"], "d26": ["汉语翻译"], "d27": ["汉语眼动"],
        "d28": ["阅读连贯"],
    }
    return mapping.get(candidate["qid"], []), None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", nargs="+", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    existing_keys = set()
    branch_rows = {branch: existing(BASE / branch / "sources.jsonl") for branch in BRANCHES}
    for branch, rows in branch_rows.items():
        for row in rows:
            existing_keys.add((row.get("doi") or "").lower())
            existing_keys.add(re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (row.get("title") or "").lower()))

    plan, skipped = [], []
    zh_counter = next_zh_id(branch_rows["linguistics-zh"])
    used_intl = {r["id"] for r in branch_rows["linguistics-intl"]}

    for receipt_file in args.receipts:
        if not receipt_file.exists():
            continue
        for line in receipt_file.read_text().splitlines():
            if not line.strip():
                continue
            candidate = json.loads(line)
            if candidate.get("result") not in ("downloaded", "already_present"):
                continue
            path = candidate.get("path")
            if not path or not (ROOT / path).exists():
                skipped.append((candidate.get("title"), "missing file"))
                continue
            doi = (candidate.get("doi") or "").lower()
            key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (candidate.get("title") or "").lower())
            if (doi and doi in existing_keys) or (key and key in existing_keys):
                skipped.append((candidate.get("title"), "duplicate"))
                continue
            # Re-derive facts from the file itself; never trust receipt strings alone.
            data = (ROOT / path).read_bytes()
            try:
                from pypdf import PdfReader
                pages = len(PdfReader(ROOT / path).pages)
            except Exception as exc:  # noqa: BLE001
                skipped.append((candidate.get("title"), f"unreadable: {exc}"))
                continue
            branch = candidate["branch"] if candidate["branch"] in BRANCHES else "linguistics-intl"
            if branch == "linguistics-zh":
                source_id = f"ZH{zh_counter:03d}-r7oa"
                zh_counter += 1
            else:
                base = "INTL-R7-" + author_slug(candidate)
                source_id, suffix = base, 1
                while source_id in used_intl:
                    suffix += 1
                    source_id = f"{base}-{suffix}"
                used_intl.add(source_id)
            record = build_record(candidate, branch, branch_rows[branch], path,
                                  pages, hashlib.sha256(data).hexdigest(), len(data), source_id)
            plan.append((branch, record))
            existing_keys.add(doi)
            existing_keys.add(key)

    print(f"planned {len(plan)} records; skipped {len(skipped)}")
    for branch, record in plan[:8]:
        print(f"  {branch}:{record['id']}  {record['year']}  {str(record['title'])[:70]}")
    if len(plan) > 8:
        print(f"  … {len(plan) - 8} more")
    if skipped[:5]:
        print("skipped:", skipped[:5])
    if not args.apply:
        return

    merge_log = []
    for branch, record in plan:
        path = BASE / branch / "sources.jsonl"
        with path.open("a") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        merge_log.append({"branch": branch, "id": record["id"], "title": record["title"],
                          "doi": record.get("doi"), "query_ids": record["query_ids"],
                          "pages": record["files"][0]["page_count"],
                          "bytes": record["files"][0]["bytes"],
                          "action": "appended", "date": TODAY})
    (BASE / "acquisition/round7/merge-log.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in merge_log) + "\n")
    print(f"appended {len(merge_log)} records")


if __name__ == "__main__":
    main()
