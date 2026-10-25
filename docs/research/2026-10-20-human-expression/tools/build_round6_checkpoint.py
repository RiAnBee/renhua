#!/usr/bin/env python3
"""Save actual integrated R6 state without declaring pending routes/final review done.

Run after source proposal merge, catalog/queue rebuild, PDF audit and generic
validation. Strict build_round6_summary.py and validate_round6.py remain the
final gates; this separate checkpoint never writes their final outputs.
"""
import collections
import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/research/2026-10-20-human-expression'
OUT=BASE/'fulltext-round6'
FROZEN=ROOT/'.harness/research-20261020/round6/baseline'
EXPECTED={'frozen-manifest.json':'514bd84cc79674467ff84cb348afd8407cc8d8014a58fd466a3b3adcebd56209',
'acquisition/pending-access.jsonl':'cc1b785b5c6013c7046c76406adfd599d5ca62c939d78ac53a64ba455a16f161',
'acquisition/pdf-files.jsonl':'c6287477479ab7d13425b9af88c0d7a14f42518d4a4bd81d990ce5aa57941396'}
PENDING={'pending','in_progress','new_route_investigation_pending','not_started','awaiting_human_verification'}
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def indexed(a,key):
 d={r[key]:r for r in a}
 if len(d)!=len(a):raise ValueError('Duplicate '+key)
 return d
def digest(o):return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def main():
 for name,want in EXPECTED.items():
  if hashlib.sha256((FROZEN/name).read_bytes()).hexdigest()!=want:raise ValueError('Frozen drift '+name)
 before=indexed(rows(FROZEN/'acquisition/pending-access.jsonl'),'record_id')
 after=indexed(rows(BASE/'acquisition/pending-access.jsonl'),'record_id')
 oldpdf=indexed(rows(FROZEN/'acquisition/pdf-files.jsonl'),'path')
 pdf=indexed(rows(BASE/'acquisition/pdf-files.jsonl'),'path')
 assert len(before)==62 and len(oldpdf)==102
 for k,r in oldpdf.items():
  if k not in pdf or any(r.get(f)!=pdf[k].get(f) for f in ('sha256','bytes','pages')):raise ValueError('Old PDF drift '+k)
 newpdf=[r for k,r in pdf.items() if k not in oldpdf]
 if len({r['sha256'] for r in newpdf})!=len(newpdf):raise ValueError('Duplicate new PDF hash')
 if {r['sha256'] for r in newpdf}&{r['sha256'] for r in oldpdf.values()}:raise ValueError('New path duplicates old file')
 reading=indexed(rows(BASE/'acquisition/reading-queue.jsonl'),'record_id')
 if set(reading)&set(after):raise ValueError('Queue overlap')
 statuses=indexed([r for p in sorted(OUT.glob('*-status.jsonl')) for r in rows(p)],'record_id')
 if set(statuses)!=set(before):raise ValueError('Frozen route scope changed')
 if any(not r.get('round6_attempts') for r in statuses.values()):raise ValueError('No actual R6 attempt')
 terminal=[];unfinished=[]
 for k,r in statuses.items():
  state=next((r.get(f) for f in ('terminal_status','result_status','investigation_status') if r.get(f)),None)
  if r.get('is_final',True) is True and state and state not in PENDING and r.get('investigation_status') not in PENDING:terminal.append(k)
  else:unfinished.append({'record_id':k,'terminal_status':state,'investigation_status':r.get('investigation_status'),'is_final':r.get('is_final'),'next_action':r.get('next_action')})
 cards={};ids=set()
 for p in sorted(OUT.glob('*cards.jsonl')):
  a=rows(p);cards[p.name]=len(a)
  for r in a:
   k=r.get('card_id',r.get('id'))
   if not k or k in ids:raise ValueError('Missing/duplicate card id '+str(k))
   ids.add(k)
 catalog=indexed(rows(BASE/'catalog.jsonl'),'record_id');oldcat=indexed(rows(FROZEN/'catalog.jsonl'),'record_id')
 changes=[]
 for p in sorted(FROZEN.glob('*/sources.jsonl')):
  branch=p.parent.name;old=indexed(rows(p),'id');current=indexed(rows(BASE/branch/'sources.jsonl'),'id')
  if set(old)-set(current):raise ValueError('Removed source '+branch)
  for k,r in current.items():
   prior=old.get(k)
   if prior!=r:changes.append({'record_id':branch+':'+k,'new_record':prior is None,'changed_fields':sorted(f for f in set(prior or {})|set(r) if (prior or {}).get(f)!=r.get(f)),'before_sha256':digest(prior) if prior else None,'after_sha256':digest(r)})
 validation=json.loads((BASE/'validation.json').read_text())
 if not validation.get('passed'):raise ValueError('Generic package validation has not passed')
 result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checked_at_cst':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
 'phase':'integrated_checkpoint_not_final_round_acceptance','is_final':False,'final_acceptance_passed':False,
 'frozen_baseline':62,'frozen_chinese':26,'frozen_international_and_other':36,'baseline_hashes':EXPECTED,
 'route_investigation_records':len(statuses),'terminal_investigation_records':len(terminal),'unfinished_investigations':unfinished,
 'closed_baseline_records':len(set(before)-set(after)),'closed_baseline_ids':sorted(set(before)-set(after)),
 'retained_baseline_records':len(set(before)&set(after)),'new_pending_ids':sorted(set(after)-set(before)),
 'current_pending_records':len(after),'current_pending_book_records':sum(r.get('reason')=='complete_book_not_obtained' for r in after.values()),
 'current_available_reading_records':len(reading),'generated_queue_identity_overlap':[],
 'current_source_records':len(catalog),'new_source_records':sorted(set(catalog)-set(oldcat)),
 'current_read_status':dict(collections.Counter(r['read_status'] for r in catalog.values())),
 'baseline_pdf_files':len(oldpdf),'new_pdf_files':len(newpdf),'new_pdf_pages':sum(r['pages'] for r in newpdf),'new_pdf_bytes':sum(r['bytes'] for r in newpdf),
 'new_pdf_paths':sorted(r['path'] for r in newpdf),'current_pdf_files':len(pdf),'current_pdf_pages':sum(r['pages'] for r in pdf.values()),'current_pdf_bytes':sum(r['bytes'] for r in pdf.values()),
 'cnki_receipts':len(rows(BASE/'acquisition/cnki-receipts.jsonl')),
 'analysis_cards':len(ids),'analysis_cards_by_file':cards,'changed_source_records':len(changes),
 'generic_package_validation_passed':True,
 'note':'Checkpoint counts are actual rebuilt state. Pending human verification is not access failure, absence of subscription, a completed route, or final acceptance. File/body acquisition, original layout, actual reading and editing effects remain distinct.'}
 save(OUT/'checkpoint-summary.json',result)
 (OUT/'checkpoint-source-merge-log.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in changes))
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
