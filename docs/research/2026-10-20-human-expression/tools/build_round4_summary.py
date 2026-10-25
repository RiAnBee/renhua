#!/usr/bin/env python3
"""Reconcile round4 against its immutable 65-record baseline.

Run after catalog, queues and PDF audit. Requires the retained private baseline;
never replaces it. Does not infer new reading or validate source conclusions.
The four-classic reading scope is the frozen round4 scope, not all future work.
"""
from pathlib import Path
import json, hashlib, datetime, collections

root = Path(__file__).resolve().parents[4]
base = root/'docs/research/2026-10-20-human-expression'
frozen = root/'.harness/research-20261020/round4/baseline'
def readl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

baseline_path = frozen/'acquisition/pending-access.jsonl'
if hashlib.sha256(baseline_path.read_bytes()).hexdigest() != '855a0fc864e49cbcec2ebeaed0f294aeb9aaa5dcbf2c69c1b5d060a529536aa5':
    raise ValueError('Frozen 65-record baseline changed; preserve and investigate, never replace it')
before = {r['record_id']: r for r in readl(baseline_path)}
after = {r['record_id']: r for r in readl(base/'acquisition/pending-access.jsonl')}
assert len(before) == 65
closed = sorted(set(before) - set(after))
retained = sorted(set(before) & set(after))
added = sorted(set(after) - set(before))
assert len(closed) + len(retained) == 65
pdf = readl(base/'acquisition/pdf-files.jsonl')
new_pdf = [r for r in pdf if r['path'].startswith('papers/human-expression/round4/')]
baseline_ids = {r['record_id'] for r in readl(frozen/'catalog.jsonl')}
catalog = readl(base/'catalog.jsonl')
source_ids = {r['record_id'] for r in catalog}
summary = dict(
    checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    frozen_baseline=65,
    baseline_book_target_records=48,
    closed_baseline_records=len(closed), closed_baseline_ids=closed,
    retained_baseline_records=len(retained), retained_baseline_ids=retained,
    new_pending_records=len(added), new_pending_ids=added,
    current_pending_records=len(after),
    current_pending_book_records=sum(r['reason']=='complete_book_not_obtained' for r in after.values()),
    new_source_records=sorted(source_ids-baseline_ids),
    new_pdf_files=len(new_pdf), new_pdf_pages=sum(r['pages'] for r in new_pdf),
    new_pdf_bytes=sum(r['bytes'] for r in new_pdf),
    new_pdf_hashes=len({r['sha256'] for r in new_pdf}),
    current_source_records=len(catalog),
    current_available_reading_records=len(readl(base/'acquisition/reading-queue.jsonl')),
    current_read_status=dict(collections.Counter(r['read_status'] for r in catalog)),
    classic_versions=4, classic_analysis_cards=41, classic_distinct_printed_pages=97,
    note='Baseline identities remain fixed. New editions/papers do not count as closing old gaps. Complete HTML body bundles and body transcriptions are separate from native PDF/layout. Classic figures are designated reading extents, not complete books or independent studies.'
)
(base/'fulltext-round4/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
log=[]
for path in sorted(frozen.glob('*/sources.jsonl')):
    branch=path.parent.name
    old={r['id']:r for r in readl(path)}
    for row in readl(base/branch/'sources.jsonl'):
        previous=old.get(row['id'])
        if previous==row: continue
        changed=sorted(k for k in set(previous or {})|set(row) if (previous or {}).get(k)!=row.get(k))
        log.append(dict(record_id=branch+':'+row['id'],new_record=previous is None,
            changed_fields=changed,baseline_source=str(path.relative_to(root)),
            before_sha256=digest(previous) if previous else None,after_sha256=digest(row)))
(base/'fulltext-round4/source-merge-log.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in log))
print(json.dumps(summary,ensure_ascii=False))
