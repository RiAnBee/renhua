#!/usr/bin/env python3
"""Reconcile round5 with frozen61 and the frozen95-PDF path+hash registry.

Run after source integration, catalog/queue rebuilding and PDF audit. This only
writes fulltext-round5/summary.json and source-merge-log.jsonl. No acquisition,
reading inference, historic round4 rewrites or runtime edits occur here.
"""
import collections
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-20-human-expression'
OUT = BASE / 'fulltext-round5'
FROZEN = ROOT / '.harness/research-20261020/round5/baseline'
PENDING_SHA = 'a4c20aae3a3c88db67330ddec7ba2f30d8115a63bfa005792ad8a608cfe1486d'
PDF_REGISTRY_SHA = 'f9ed5636421b519034db587697f1939e794c9b7566d832b1203723fdc9d4cfe2'
PENDING_STATES = {'pending', 'in_progress', 'new_route_investigation_pending', 'not_started'}


def readl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def require_sha(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Frozen baseline changed: ' + str(path.relative_to(ROOT)))


def keyed(rows, field, context):
    result = {row[field]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate identities: ' + context)
    return result


def main():
    before_path = FROZEN / 'acquisition/pending-access.jsonl'
    pdf_path = FROZEN / 'acquisition/pdf-files.jsonl'
    require_sha(before_path, PENDING_SHA)
    require_sha(pdf_path, PDF_REGISTRY_SHA)
    before = keyed(readl(before_path), 'record_id', 'frozen pending')
    after = keyed(readl(BASE / 'acquisition/pending-access.jsonl'), 'record_id', 'current pending')
    zh = {key for key in before if key.startswith('linguistics-zh:')}
    if len(before) != 61 or len(zh) != 26:
        raise ValueError('Round5 scope must remain frozen61 = ZH26 + other35')
    closed, retained, added = (sorted(values) for values in (
        set(before)-set(after), set(before)&set(after), set(after)-set(before)))
    old_pdfs = keyed(readl(pdf_path), 'path', 'frozen PDF paths')
    pdfs = keyed(readl(BASE / 'acquisition/pdf-files.jsonl'), 'path', 'current PDF paths')
    if len(old_pdfs) != 95:
        raise ValueError('Expected95 baseline PDF paths')
    for path, row in old_pdfs.items():
        if path not in pdfs or any(row.get(key) != pdfs[path].get(key) for key in ('sha256', 'bytes', 'pages')):
            raise ValueError('Existing PDF registry drift; do not treat replacement/deletion as a new acquisition: ' + path)
    baseline_pairs = {(row['path'], row['sha256']) for row in old_pdfs.values()}
    new_pdf = [row for row in pdfs.values() if (row['path'], row['sha256']) not in baseline_pairs]
    old_hashes = {row['sha256'] for row in old_pdfs.values()}
    catalog = keyed(readl(BASE / 'catalog.jsonl'), 'record_id', 'current catalog')
    old_catalog = keyed(readl(FROZEN / 'catalog.jsonl'), 'record_id', 'frozen catalog')
    status_files = sorted(OUT.glob('*-status.jsonl'))
    statuses = {}
    for path in status_files:
        for row in readl(path):
            key = row['record_id']
            if key in statuses:
                raise ValueError('Duplicate round5 status: ' + key)
            statuses[key] = row
    if set(statuses) != set(before):
        raise ValueError('Round5 status identities must equal the frozen61 before final summary')
    counts = collections.Counter()
    finished = set()
    for key, row in statuses.items():
        state = next((row.get(k) for k in ('terminal_status', 'result_status', 'investigation_status') if row.get(k)), None)
        counts[str(state)] += 1
        if (state and state not in PENDING_STATES and row.get('is_final', True) is True
                and row.get('investigation_status') not in PENDING_STATES
                and row.get('round5_attempts')):
            finished.add(key)
    if finished != set(before):
        raise ValueError('Round5 route investigations still intermediate; do not write a final summary')
    cards = {}
    ids = set()
    for path in sorted(OUT.glob('*cards.jsonl')):
        rows = readl(path)
        for row in rows:
            key = row.get('card_id', row.get('id'))
            if not key or key in ids:
                raise ValueError('Missing/duplicate analysis card ID: ' + str(key))
            ids.add(key)
        cards[path.name] = len(rows)
    # Patch log covers every frozen branch, including practice/citation sources.
    # The stable per-source before/after hash is a change locator, not a claim
    # that every field change has already passed semantic independent review.
    merge_log = []
    for path in sorted(FROZEN.glob('*/sources.jsonl')):
        branch = path.parent.name
        old = keyed(readl(path), 'id', 'frozen ' + branch)
        current = keyed(readl(BASE / branch / 'sources.jsonl'), 'id', 'current ' + branch)
        removed = set(old)-set(current)
        if removed:
            raise ValueError('Baseline sources removed: ' + repr(sorted(removed)))
        for key, row in current.items():
            previous = old.get(key)
            if previous == row:
                continue
            changed = sorted(k for k in set(previous or {}) | set(row) if (previous or {}).get(k) != row.get(k))
            merge_log.append(dict(record_id=branch + ':' + key, new_record=previous is None,
                changed_fields=changed, baseline_source=str(path.relative_to(ROOT)),
                before_sha256=digest(previous) if previous else None, after_sha256=digest(row)))
    summary = dict(
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        research_dates='2026-10-20 through 2026-10-21',
        frozen_baseline=61, frozen_chinese=26, frozen_international_and_other=35,
        baseline_pending_sha256=PENDING_SHA, baseline_pdf_registry_sha256=PDF_REGISTRY_SHA,
        baseline_book_target_records=sum(row.get('reason') == 'complete_book_not_obtained' for row in before.values()),
        route_investigation_records=len(statuses), terminal_investigation_records=len(finished),
        route_terminal_status_counts=dict(counts),
        closed_baseline_records=len(closed), closed_baseline_ids=closed,
        retained_baseline_records=len(retained), retained_baseline_ids=retained,
        new_pending_records=len(added), new_pending_ids=added,
        current_pending_records=len(after),
        current_pending_book_records=sum(row.get('reason') == 'complete_book_not_obtained' for row in after.values()),
        new_source_records=sorted(set(catalog)-set(old_catalog)),
        baseline_pdf_files=len(old_pdfs), new_pdf_files=len(new_pdf),
        new_pdf_pages=sum(row['pages'] for row in new_pdf), new_pdf_bytes=sum(row['bytes'] for row in new_pdf),
        new_pdf_hashes=len({row['sha256'] for row in new_pdf}),
        new_pdf_unique_hashes_not_in_baseline=len({row['sha256'] for row in new_pdf}-old_hashes),
        new_pdf_file_paths=sorted(row['path'] for row in new_pdf),
        new_pdf_selection='Frozen versus current (path, SHA256) pairs, with preexisting-path drift rejected; directory names are not selection criteria',
        current_source_records=len(catalog),
        current_available_reading_records=len(readl(BASE / 'acquisition/reading-queue.jsonl')),
        current_read_status=dict(collections.Counter(row['read_status'] for row in catalog.values())),
        analysis_cards=len(ids), analysis_cards_by_file=cards, changed_source_records=len(merge_log),
        note='Bounded route review, body acquisition, native PDF/layout and actual reading are distinct. New source versions or partial books do not clear a frozen full-book gap. Existing-source rereading and multiple receipts do not multiply new PDF files or independent studies.'
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'source-merge-log.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in merge_log))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
