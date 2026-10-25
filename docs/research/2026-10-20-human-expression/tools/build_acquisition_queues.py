#!/usr/bin/env python3
"""Keep missing full text separate from available documents needing reading."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/research/2026-10-20-human-expression"
BOOK_TYPES = {"book", "edited_book", "edited-book", "open_book"}


def values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from values(item)
    elif isinstance(value, list):
        for item in value:
            yield from values(item)


def main():
    pending, reading = [], []
    for source in sorted(BASE.glob("*/sources.jsonl")):
        for line in source.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            branch = source.parent.name
            book = row.get("type") in BOOK_TYPES
            status = row.get("read_status")
            access = (row.get("access_status") or "").lower()
            document_paths = [value for value in values(row)
                         if value.endswith((".pdf", ".epub")) and "papers/" in value
                         and not value.startswith(("https://", "http://"))]
            # A book outside open-books can also have a verified full copy;
            # conversely, a sample/frontmatter PDF is not a complete book.
            # An explicitly verified, locally saved complete HTML edition is
            # readable full text too. A live TOC, sample, or selected scan is not.
            bundle = row.get("fulltext_bundle_manifest")
            complete_html_bundle = (
                row.get("full_book_format") == "html_bundle"
                and row.get("complete_book_body_html") is True
                and isinstance(bundle, str)
                and bundle.startswith("papers/human-expression/")
                and (ROOT / bundle).is_file()
            )
            complete_book = (book and row.get("full_book_obtained") is True
                             and (bool(document_paths) or complete_html_bundle))
            readable_full = row.get("fulltext_available") is True or bool(document_paths) or any(part in access for part in
                ("full_html", "fulltext_html", "fulltext_saved", "public_html_verified", "public_html_read"))
            missing = (book and not complete_book) or (
                (status in ("metadata", "abstract") or "fulltext_pending" in access
                 or row.get("fulltext_available") is False) and not readable_full
                and row.get("type") != "collection-entry")
            item = dict(record_id=branch + ":" + row["id"], title=row["title"],
                        authors=row.get("authors"), year=row.get("year"),
                        type=row.get("type"), canonical_url=row.get("canonical_url"),
                        metadata_url=row.get("metadata_url"), doi=row.get("doi"),
                        isbn=row.get("isbn"), read_status=status, access_status=access,
                        priority=row.get("priority", "P1_book" if book else "P2_article"),
                        source_record_file=str(source.relative_to(ROOT)))
            if row.get('online_full_book_available') or row.get('online_alternate_edition_available'):
                item.update(online_full_book_available=row.get('online_full_book_available', False),
                            online_alternate_edition_available=row.get('online_alternate_edition_available', False),
                            school_access_round3=row.get('school_access_round3'))
            for field in ('school_access_round4', 'online_late_chapters_available', 'school_online_url'):
                if field in row:
                    item[field] = row[field]
            if missing:
                item.update(reason="complete_book_not_obtained" if book else "fulltext_not_obtained_or_not_verified",
                    next_action="出版社或校图书馆核对准确版本与可读范围；样章不算整书" if book
                    else "复用原站/作者合法开放本，或学校已授权数据库；保留摘要推导边界")
                if row.get('online_full_book_available'):
                    item['next_action'] = '准确版本已可学校在线阅读；先做定位阅读，本地整书文件另补，不重新申请已存在的在线权限'
                elif row.get('online_alternate_edition_available'):
                    item['next_action'] = '学校有可读异版；按回执定位并标明版本，目标ISBN的本地整书仍待补，勿混同'
                elif row.get('online_late_chapters_available'):
                    item['next_action'] = '学校正常网页晚部章节可读；按回执定位阅读，其他章节权限及本地整书另核，不把结语可读当全书已取得'
                pending.append(item)
            elif status != "full":
                item.update(reason="available_document_or_collection_needs_located_reading",
                            next_action="先读现有文档/网页集合；核卡中范围，不重复下载")
                reading.append(item)
    out = BASE / "acquisition"
    for name, rows in (("pending-access.jsonl", pending), ("reading-queue.jsonl", reading)):
        (out / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    summary = dict(pending_access=len(pending),
                   pending_complete_books=sum(row["type"] in BOOK_TYPES for row in pending),
                   available_reading_records=len(reading),
                   pending_by_branch=dict(collections.Counter(row["record_id"].split(":")[0] for row in pending)),
                   note="Records, not unique works. Complete verified local HTML book bundles count as acquired body text; original PDF/layout gaps remain explicit in their source cards. TOCs, samples and online-only selected scans do not count as complete local books.")
    (out / "queue-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
