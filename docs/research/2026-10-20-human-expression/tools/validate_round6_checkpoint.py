#!/usr/bin/env python3
"""Read-only evidence audit of an explicitly intermediate round6 checkpoint.

Writes only the selected checkpoint stem's .{json,md} (default preserves the
original review-checkpoint-round6 names). Never writes a final review,
closes an access gap, applies a source proposal, or relaxes validate_round6.py.
Only the two known live school-verification investigations may be deferred;
other identity/hash/meaning/merge failures remain checkpoint failures.
"""
import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

HELPER = Path(__file__).with_name('validate_round6.py')
SPEC = importlib.util.spec_from_file_location('round6_checkpoint_helpers', HELPER)
r6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r6)
LIVE_VERIFICATION_IDS = {'reading-cognition:RC006', 'reading-cognition:RC007'}


def check_checkpoint_products(audit, sources, before, frozen, old_pdfs, statuses, pdfs):
    """Recalculate the current checkpoint; never substitute it for final scope."""
    summary = audit.load(r6.ROUND / 'checkpoint-summary.json')
    acq, reading = audit.sections['acquisition'], audit.sections['reading']
    unfinished = []
    terminal = 0
    for key, row in statuses.items():
        state = r6.pick(row, 'terminal_status', 'result_status', 'investigation_status')
        if (row.get('is_final', True) is True and state in r6.TERMINAL_STATES
                and row.get('investigation_status') not in r6.PENDING_STATES):
            terminal += 1
        else:
            unfinished.append({'record_id': key, 'terminal_status': state,
                'investigation_status': row.get('investigation_status'),
                'is_final': row.get('is_final'), 'next_action': row.get('next_action')})
    pending = r6.unique_rows(audit, audit.load(r6.BASE / 'acquisition/pending-access.jsonl'),
                             'checkpoint current pending')
    old_paths = {row.get('path') for row in old_pdfs}
    actual_changes = {key for key, value in sources.items() if before.get(key) != value}
    expected = {
        'phase': 'integrated_checkpoint_not_final_round_acceptance',
        'is_final': False, 'final_acceptance_passed': False,
        'frozen_baseline': len(frozen),
        'frozen_chinese': sum(key.startswith('linguistics-zh:') for key in frozen),
        'frozen_international_and_other': sum(not key.startswith('linguistics-zh:') for key in frozen),
        'baseline_hashes': {name: hashlib.sha256((r6.FROZEN/name).read_bytes()).hexdigest()
            for name in ('frozen-manifest.json', 'acquisition/pending-access.jsonl', 'acquisition/pdf-files.jsonl')},
        'route_investigation_records': len(statuses), 'terminal_investigation_records': terminal,
        'closed_baseline_records': len(acq['frozen_ids_cleared_from_file_queue']),
        'closed_baseline_ids': acq['frozen_ids_cleared_from_file_queue'],
        'retained_baseline_records': len(acq['frozen_ids_remaining_in_file_queue']),
        'new_pending_ids': acq['new_pending_identities_outside_frozen_scope'],
        'current_pending_records': len(pending),
        'current_pending_book_records': sum(row.get('reason') == 'complete_book_not_obtained' for row in pending.values()),
        'current_available_reading_records': acq['current_reading_queue_total'],
        'generated_queue_identity_overlap': acq['generated_queue_identity_overlap'],
        'current_source_records': len(sources), 'new_source_records': sorted(set(sources)-set(before)),
        'current_read_status': dict(collections.Counter(row.get('read_status') for row in sources.values())),
        'baseline_pdf_files': len(old_pdfs), 'new_pdf_files': acq['new_registered_pdfs'],
        'new_pdf_pages': acq['new_pdf_pages'], 'new_pdf_bytes': acq['new_pdf_bytes'],
        'new_pdf_paths': sorted(row['path'] for row in pdfs if row.get('path') not in old_paths),
        'current_pdf_files': len(pdfs), 'current_pdf_pages': sum(row.get('pages', 0) for row in pdfs),
        'current_pdf_bytes': sum(row.get('bytes', 0) for row in pdfs),
        'cnki_receipts': len(audit.load(r6.BASE / 'acquisition/cnki-receipts.jsonl')),
        'analysis_cards': reading['card_records'], 'analysis_cards_by_file': reading['by_file'],
        'changed_source_records': len(actual_changes),
        'generic_package_validation_passed': audit.sections['global_delivery']['passed_flag'],
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            audit.error('checkpoint_summary_drift', field)
    reported_unfinished = r6.unique_rows(audit, summary.get('unfinished_investigations', []),
                                        'checkpoint summary unfinished')
    if reported_unfinished != {row['record_id']: row for row in unfinished}:
        audit.error('checkpoint_unfinished_identity_or_fields_drift', repr(sorted(reported_unfinished)))
    log = r6.unique_rows(audit, audit.load(r6.ROUND / 'checkpoint-source-merge-log.jsonl'),
                         'checkpoint source merge log')
    if set(log) != actual_changes:
        audit.error('checkpoint_merge_log_changed_identity_scope', repr(sorted(set(log)^actual_changes)))
    def digest(row):
        return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    for key, record in log.items():
        if key not in sources:
            continue
        old, current = before.get(key), sources[key]
        fields = sorted(field for field in set(old or {}) | set(current)
                        if (old or {}).get(field) != current.get(field))
        if (record.get('before_sha256') != (digest(old) if old else None)
                or record.get('after_sha256') != digest(current)
                or record.get('changed_fields') != fields
                or record.get('new_record') is not (old is None)):
            audit.error('checkpoint_source_merge_log_field_or_hash_drift', key)
    audit.sections['checkpoint_products'] = {'summary_fields_checked': sorted(expected),
        'unfinished_records_checked': len(unfinished), 'changed_source_records': len(actual_changes),
        'merge_log_records': len(log), 'all_before_after_field_hashes_checked': True,
        'product_file_sha256': {name: hashlib.sha256((r6.ROUND/name).read_bytes()).hexdigest()
            for name in ('checkpoint-summary.json', 'checkpoint-source-merge-log.jsonl')},
        'scope': 'Actual current integrated checkpoint only; does not replace the strict final summary or final audit.'}


def check_supplemental_routes(audit, sources):
    rows = audit.load(r6.ROUND / 'root-route-notes.jsonl')
    seen, count = set(), 0
    for row in rows:
        key = row.get('route_note_id')
        if not key or key in seen:
            audit.error('supplemental_route_note_missing_or_duplicate_id', str(key))
        seen.add(key)
        if not row.get('record_ids') or not set(row['record_ids']).issubset(sources):
            audit.error('supplemental_route_unknown_source', str(key))
        if not row.get('observed_status') or not row.get('observed_outcome') or not row.get('counting_note'):
            audit.error('supplemental_route_observation_or_counting_scope_missing', str(key))
        if not row.get('files'):
            audit.error('supplemental_route_without_evidence', str(key))
        for ref in row.get('files', []):
            audit.file(ref.get('path'), ref.get('sha256'), ref.get('bytes'),
                context='supplemental route '+str(key), require_hash=True, require_size=True)
            count += 1
        if 'linguistics-intl:INTL-SHEN-1989' in row.get('record_ids', []):
            refs = [ref.get('path', '') for ref in row.get('files', [])]
            if not any(path.endswith('Shen1989-NJU-authed-real-gateway-result.dom.txt') for path in refs):
                audit.error('shen_current_route_missing_actual_gateway_dom', str(key))
    audit.sections['supplemental_routes'] = {'route_notes': len(rows), 'evidence_file_references': count,
        'scope': 'Additional actual route evidence; never extra frozen targets, acquisitions or terminal overrides.'}


def check_local_markdown_links(audit):
    checked = 0
    # Resolve local file links only, including relative image links. Network URLs
    # and same-document fragments do not establish file acquisition or meaning.
    for path in [r6.ROOT/'README.md', *sorted(r6.BASE.rglob('*.md'))]:
        for match in re.finditer(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', path.read_text()):
            target = match.group(1).strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            # Codex file links may carry a line locator, e.g. report.md:83.
            local = Path(r6.locator_path(unquote(parsed.path)))
            local = local if local.is_absolute() else path.parent/local
            checked += 1
            if not local.exists():
                audit.error('checkpoint_local_markdown_link_missing', audit.relative(path)+': '+target)
    audit.sections['checkpoint_local_links'] = {'local_file_links_checked': checked,
        'scope': 'Current local Markdown file targets only; not remote availability, anchor semantics or proof of full-text access.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--output-stem', default='review-checkpoint-round6',
        help='Checkpoint report basename within the research directory; omit the extension.')
    args = parser.parse_args()
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.output_stem)
            or args.output_stem.endswith(('.json', '.md'))
            or not args.output_stem.startswith('review-checkpoint-')):
        parser.error('--output-stem must be a checkpoint basename beginning review-checkpoint-, without a path or extension')
    audit = r6.Audit()
    frozen, old_pdfs = r6.check_baseline(audit)
    sources, before = r6.source_map(audit, r6.BASE), r6.source_map(audit, r6.FROZEN)
    statuses = r6.check_statuses(audit, sources, frozen)
    receipts, pdfs = r6.check_acquisition(audit, sources, before, frozen, statuses, old_pdfs)
    r6.check_manifests_and_reading(audit, sources)
    r6.check_proposals(audit, sources, before)
    r6.check_global_summary(audit, sources, pdfs)
    r6._r4.check_protected_runtime(audit)
    acq = audit.sections['acquisition']
    closures = (set(acq['frozen_ids_cleared_from_file_queue'])
                | set(acq['newly_marked_complete_book_records'])
                | set(acq['newly_marked_complete_chapter_body_records']))
    r6.check_manual_readback(audit, final=False, cleared=closures)
    r6.check_public_content(audit, receipts)

    # This checkpoint has distinct, explicitly nonfinal summary and merge log.
    # Also check applied sources independently against frozen-plus-proposal data.
    expected = {key: dict(value) for key, value in before.items()}
    seen = set()
    for path in sorted(r6.ROUND.glob('*-source-updates.jsonl')):
        for row in audit.load(path):
            key = row['record_id']
            if key in seen:
                audit.error('checkpoint_competing_source_proposals', key)
            seen.add(key)
            expected[key] = {**expected.get(key, {}), **row.get('updates', {})}
    if sources != expected:
        drift = sorted(key for key in set(sources)|set(expected) if sources.get(key) != expected.get(key))
        audit.error('checkpoint_integrated_sources_differ_from_frozen_proposals', repr(drift))
    audit.sections['checkpoint_merge'] = {'proposal_identities': len(seen),
        'source_records': len(sources), 'exact_frozen_plus_proposals_equal_current': sources == expected,
        'final_summary_and_final_merge_log': 'deferred; this checkpoint does not create them'}
    check_checkpoint_products(audit, sources, before, frozen, old_pdfs, statuses, pdfs)
    check_supplemental_routes(audit, sources)
    check_local_markdown_links(audit)

    live = {key for key, row in statuses.items() if key in LIVE_VERIFICATION_IDS
            and row.get('is_final') is False
            and r6.pick(row, 'terminal_status', 'result_status', 'investigation_status') in r6.PENDING_STATES}
    deferred, failures = [], []
    for issue in audit.errors:
        if (issue['code'] in {'investigation_still_pending', 'investigation_marker_pending', 'explicitly_intermediate_status'}
                and any(issue['detail'] == key or issue['detail'].startswith(key + ':') for key in live)):
            deferred.append(issue)
        else:
            failures.append(issue)
    deferred.extend([
        {'code': 'strict_round6_final_summary_not_accepted_at_checkpoint',
         'detail': 'Final62-terminal summary and strict merge log are not substituted by checkpoint counts.'},
        {'code': 'two_live_routes_then_formal_final_integration_and_readback',
         'detail': 'Current checkpoint entries are integrated. Await the two actual access outcomes, then update any resulting proposals/files/queues and formal summary before an explicitly requested final audit; no review-final-round6 pass is emitted.'},
    ])
    result = {'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phase': 'independent_intermediate_checkpoint', 'is_final': False,
        'final_acceptance_passed': False, 'checkpoint_static_checks_passed': not failures,
        'live_manual_verification_record_ids': sorted(live), 'checks': audit.sections,
        'unique_files_hash_checked': len(audit.hashed_files), 'errors': failures,
        'deferred_final_requirements': deferred, 'warnings': audit.warnings,
        'limits': 'Current evidence consistency and sampled meaning only. This is neither62terminal completion nor complete acquisition, originalPDF collation, full-book semantic reading or editing-effect validation.'}
    (r6.BASE/(args.output_stem+'.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    reading, scope = audit.sections['reading'], audit.sections['frozen_scope']
    lines = ['# 第六轮检查点独立核验', '',
             '本检查点静态检查：' + ('通过' if not failures else '未通过') + '。本轮尚未最终验收，不能据此称62项全终态或全部全文已取得。', '',
             f'冻结62项（中文26、其余36）；当前终态{scope["terminal_investigations"]}/62；待人工记录：' + '、'.join(sorted(live)) + '。', '',
             f'当前核{reading["card_records"]}卡、{len(sources)}来源；新注册PDF{acq["new_registered_pdfs"]}份/{acq["new_pdf_pages"]}页；原62闭{len(acq["frozen_ids_cleared_from_file_queue"])}、留{len(acq["frozen_ids_remaining_in_file_queue"])}。这是实际当前文件口径，非预定数量。', '',
             f'检查点摘要{len(audit.sections["checkpoint_products"]["summary_fields_checked"])}个字段、{audit.sections["checkpoint_products"]["merge_log_records"]}条来源变更的字段与前后散列逐项相符；核{len(audit.hashed_files)}个不同文件散列、{audit.sections["checkpoint_local_links"]["local_file_links_checked"]}条本地Markdown文件链接。补充路线{audit.sections["supplemental_routes"]["route_notes"]}条，仅作实际访问证据，不增调查目标或取得数。', '',
             f'独立人工抽审{len(audit.sections["manual_readback"]["findings"])}点；全部当前闭合身份已有原件结构核。原页修正与范围见[JSON]({args.output_stem}.json)。', '',
             f'通用文件校验另保留{len(audit.sections["global_delivery"]["upstream_package_warnings"])}条范围/书目提醒；PDF登记中{audit.sections["global_delivery"]["pdf_files_with_parser_warnings"]}份有解析器可恢复警告。本工具的静态错误数不抹去这些上游提醒。', '',
             '## 人工发现与已修问题', '']
    for finding in audit.sections['manual_readback']['findings']:
        if finding.get('requires_correction'):
            lines += ['- ' + finding['issue'] + ' ' + finding['resolution']]
    lines += ['', 'Hayes仅闭目标章正文，书共用参考另缺；Prince闭包含自身参考的目标章，均不计整本书。Centrality闭实质HTML书正文，原PDF/EPUB和版式仍缺。ZH055新增指定三章及结论的阅读保留partial，不因53正文页或19卡称整书通读。', '',
              '## 当前错误', '']
    lines += ['- '+x['code']+'：'+x['detail'] for x in failures] or ['无当前静态错误。']
    lines += ['', '## 最终验收仍待', '']
    lines += ['- '+x['code']+'：'+x['detail'] for x in deferred]
    lines += ['', '本工具未修改主来源、获取/阅读队列、运行时或第四/五轮历史；也未运行或写入最终验收。', '']
    (r6.BASE/(args.output_stem+'.md')).write_text('\n'.join(lines))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
