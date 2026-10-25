#!/usr/bin/env python3
"""Independently check round 6's frozen scope, evidence and integrated proposals.

No network, acquisition, source/queue rebuilding or runtime changes. Without
--final this prints a read-only preflight. Only use --final after integration;
it writes review-final-round6.{json,md}, leaving rounds 4 and 5 untouched.
Static consistency cannot establish a paper's truth or an editing benefit.
"""
import argparse
import collections
import datetime
import hashlib
import html
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-20-human-expression'
ROUND = BASE / 'fulltext-round6'
PRIVATE = ROOT / '.harness/research-20261020/round6'
FROZEN = PRIVATE / 'baseline'
BASELINE_SHA256 = 'cc1b785b5c6013c7046c76406adfd599d5ca62c939d78ac53a64ba455a16f161'
MANIFEST_SHA256 = '514bd84cc79674467ff84cb348afd8407cc8d8014a58fd466a3b3adcebd56209'
HISTORIC_HELPER_SHA256 = '30f266e5205f36110e78645d917184792cb052257db00bdf3b63462c61125bbb'

# Reuse only side-effect-free helpers. Importing the historic script does not
# invoke main(), mutate its constants, run its old scope or rewrite its result.
_helper_path = Path(__file__).with_name('validate_round4.py')
if hashlib.sha256(_helper_path.read_bytes()).hexdigest() != HISTORIC_HELPER_SHA256:
    raise RuntimeError('Historic round4 helper changed; do not import a drifted audit or overwrite its history')
_spec = importlib.util.spec_from_file_location('round4_helpers', _helper_path)
_r4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r4)
Audit, walk, strings = _r4.Audit, _r4.walk, _r4.strings
identity, pick = _r4.identity, _r4.pick
value_retained = _r4.value_retained
receipt_sources, complete_book_receipt = _r4.receipt_sources, _r4.complete_book_receipt

PENDING_STATES = _r4.PENDING_STATES | {'in_progress', 'not_started'}
TERMINAL_STATES = _r4.TERMINAL_STATES | {
    'no_new_legal_route_found', 'completed_new_route_review',
    'complete_article_body_transcription_obtained',
    'existing_complete_body_preserved', 'same_work_route_checked_no_new_file',
    'official_29page_preview_acquired_complete_book_pending',
    'author_frontmatter_attachment_link_denied',
    'new_library_catalog_metadata_only', 'new_googlebooks_metadata_no_preview',
    'new_university_ebook_lead_catalog_unavailable',
    'official_journal_historical_toc_only', 'new_oa_index_closed_no_repository_match',
    'translation_new_library_lead_english_original_restricted',
    'new_accurate_ia_edition_access_restricted', 'new_library_metadata_no_fullbook',
    'new_official_chapter_abstract_access_gated', 'no_new_legal_wholebook_route_found',
    'new_author_institution_bibliography_only', 'new_accurate_ia_book_access_restricted',
    'no_new_legal_exact_edition_route_found',
    'no_new_legal_route_found_existing_online_retained',
    'no_new_legal_file_route_existing_online_retained',
    'original_journal_new_search_no_match_reprint_linked',
    'no_new_legal_file_route_new_selected_online_reading',
    'official_six_page_frontmatter_pdf_acquired_no_book_body',
    'complete_journal_pdf_acquired_and_body_visually_read',
    'complete_chapter_body_pdf_obtained_shared_references_pending',
    'complete_chapter_pdf_obtained',
    'complete_book_body_html_obtained',
    'no_new_verified_complete_target_file',
    'new_22page_preview_obtained_complete_book_pending',
}
BOOK_TYPES = _r4.BOOK_TYPES


def file_refs(value):
    """Historic explicit aliases plus the new page-render image_path schema."""
    seen = set()
    for ref in _r4.file_refs(value):
        if ref not in seen:
            seen.add(ref)
            yield ref
    for row in walk(value):
        if isinstance(row.get('image_path'), str) and row.get('sha256'):
            ref = (row['image_path'], row['sha256'], row.get('bytes'))
            if ref not in seen:
                seen.add(ref)
                yield ref


def locator_path(value):
    """Allow a page-fragment or clearly separated Chinese locator annotation."""
    value = value.split('#', 1)[0]
    value = re.split(r'(?<=\.pdf)，|(?<=\.txt)，|(?<=\.html)，', value, maxsplit=1)[0]
    return re.sub(r':\d+(?:[-–]\d+)?$', '', value)


def check_local_evidence_paths(audit, value, context):
    for text in strings(value):
        if text.startswith(('.harness/', 'papers/', 'docs/', str(ROOT) + '/')):
            audit.file(locator_path(text), context=context)


def source_map(audit, folder):
    result = {}
    for path in sorted(folder.glob('*/sources.jsonl')):
        for row in audit.load(path):
            key = path.parent.name + ':' + str(row.get('id', ''))
            if key in result:
                audit.error('duplicate_source_id', key)
            result[key] = row
    return result


def unique_rows(audit, rows, context):
    result = {}
    for row in rows:
        key = identity(row)
        if not key:
            audit.error('missing_record_id', context)
        elif key in result:
            audit.error('duplicate_record_id', context + ': ' + key)
        else:
            result[key] = row
    return result


def check_baseline(audit):
    audit.file(str(FROZEN / 'frozen-manifest.json'), MANIFEST_SHA256,
               context='frozen round6 manifest', require_hash=True)
    manifest = audit.load(FROZEN / 'frozen-manifest.json')
    names = set()
    for row in manifest:
        name = row.get('path')
        if not isinstance(name, str) or name in names:
            audit.error('invalid_or_duplicate_frozen_file', str(name))
            continue
        names.add(name)
        p = (FROZEN / name).resolve()
        if not p.is_relative_to(FROZEN):
            audit.error('frozen_manifest_path_escape', name)
            continue
        audit.file(str(p), row.get('sha256'), context='frozen evidence', require_hash=True)
    required = {'catalog.jsonl', 'validation.json', 'delivery-round5.json',
                'review-final-round5.json', 'fulltext-round5/summary.json', 'acquisition/pending-access.jsonl',
                'acquisition/pdf-files.jsonl', 'acquisition/reading-queue.jsonl'}
    required |= {branch + '/sources.jsonl' for branch in (
        'citation-audits', 'linguistics-zh', 'supplements', 'linguistics-intl',
        'reading-cognition', 'open-books', 'practice-guides')}
    if not required.issubset(names):
        audit.error('frozen_required_files_missing', repr(sorted(required - names)))
    audit.file(str(FROZEN / 'acquisition/pending-access.jsonl'), BASELINE_SHA256,
               context='frozen 62 pending identities', require_hash=True)
    frozen = unique_rows(audit, audit.load(FROZEN / 'acquisition/pending-access.jsonl'), 'frozen scope')
    zh = {key for key in frozen if key.startswith('linguistics-zh:')}
    if len(frozen) != 62 or len(zh) != 26:
        audit.error('frozen_scope_drift', 'expected 62 = Chinese26 + international/other36')
    old_pdfs = audit.load(FROZEN / 'acquisition/pdf-files.jsonl')
    if len(old_pdfs) != 102 or len({r.get('path') for r in old_pdfs}) != 102:
        audit.error('frozen_pdf_registry_scope', 'expected 102 unique pre-round6 PDF paths')
    audit.sections['baseline'] = {
        'frozen_manifest_sha256': MANIFEST_SHA256, 'files_hash_checked': len(names),
        'pending_sha256': BASELINE_SHA256, 'pending_identities': len(frozen),
        'existing_registered_pdf_paths': len(old_pdfs),
        'new_file_selection': 'Current path+SHA256 registry minus this frozen registry; never inferred from round directory names',
    }
    historical_files = 0
    for row in audit.load(FROZEN / 'delivery-round5.json').get('files', []):
        value = row.get('path', '')
        if ('/fulltext-round5/' in value or '/fulltext-round4/' in value or '/classics-round4/' in value
                or value.endswith(('/review-final-round5.json', '/review-final-round5.md',
                                   '/review-final-round4.json', '/review-final-round4.md',
                                   '/tools/validate_round5.py', '/tools/build_round5_summary.py',
                                   '/tools/validate_round4.py', '/tools/build_round4_summary.py'))):
            audit.file(value, row.get('sha256'), row.get('bytes'),
                       'round4/5 historical artifact must remain unchanged', require_hash=True, require_size=True)
            historical_files += 1
    audit.sections['baseline']['historic_round4_and_round5_artifacts_hash_checked'] = historical_files
    prior_raw_paths = set()
    for path in sorted(FROZEN.glob('*/sources.jsonl')):
        for row in audit.load(path):
            for value, digest, size in file_refs(row):
                p = audit.file(value, digest, size, 'pre-round6 explicitly hashed original', require_hash=True)
                if p:
                    prior_raw_paths.add(audit.relative(p))
    audit.sections['baseline']['prior_source_file_hash_declarations_checked'] = len(prior_raw_paths)
    return frozen, old_pdfs


def check_statuses(audit, sources, frozen):
    zh = {key for key in frozen if key.startswith('linguistics-zh:')}
    statuses, terminal, counts = {}, set(), collections.Counter()
    for name, expected in (('chinese-status.jsonl', zh), ('international-status.jsonl', set(frozen)-zh)):
        rows = unique_rows(audit, audit.load(ROUND / name), name)
        if set(rows) != expected:
            audit.error('status_scope_mismatch', name + ': missing=' + repr(sorted(expected-set(rows)))
                        + '; extra=' + repr(sorted(set(rows)-expected)))
        for key, row in rows.items():
            statuses[key] = row
            if key not in sources:
                audit.error('unknown_status_source', key)
            state = pick(row, 'terminal_status', 'result_status', 'investigation_status')
            counts[str(state)] += 1
            if not state or state in PENDING_STATES:
                audit.error('investigation_still_pending', key + ': ' + str(state))
            elif state not in TERMINAL_STATES:
                audit.error('unknown_terminal_status', key + ': ' + str(state))
            elif row.get('is_final', True) is not True:
                audit.error('explicitly_intermediate_status', key)
            else:
                terminal.add(key)
            if row.get('investigation_status') in PENDING_STATES:
                audit.error('investigation_marker_pending', key)
            attempts = row.get('round6_attempts')
            if not isinstance(attempts, list) or not attempts:
                audit.error('no_current_round_attempt', key)
                continue
            for attempt in attempts:
                if not isinstance(attempt, dict) or not any(attempt.get(k) for k in ('outcome', 'result', 'observed')):
                    audit.error('attempt_without_observed_outcome', key)
                    continue
                # A genuine negative search can have no candidate URL. It must
                # still record what was searched and preserve its observation.
                if not any(attempt.get(k) for k in ('route', 'kind', 'query', 'query_or_url', 'entry_url', 'url')):
                    audit.error('attempt_without_route_or_query', key)
                check_local_evidence_paths(audit, attempt, 'round6 attempt ' + key)
            check_local_evidence_paths(audit, row.get('evidence_paths', []), 'round6 status ' + key)
    audit.sections['frozen_scope'] = {
        'expected': 62, 'chinese_expected': 26, 'international_and_other_expected': 36,
        'status_identities': len(statuses), 'terminal_investigations': len(terminal),
        'identities_match': set(statuses) == set(frozen),
        'all_terminal': terminal == set(frozen), 'status_counts': dict(counts),
    }
    return statuses


def check_manifests_and_reading(audit, sources):
    manifests, hashed = 0, set()
    for folder in (PRIVATE, ROOT / 'papers/human-expression/round6', ROUND):
        for path in sorted(folder.rglob('*')) if folder.exists() else []:
            if path.suffix not in {'.json', '.jsonl'} or not any(s in path.name for s in ('manifest', 'receipt', 'index')):
                continue
            if path.is_relative_to(FROZEN):
                continue
            refs = list(file_refs(audit.load(path)))
            if refs:
                manifests += 1
            for value, digest, size in refs:
                p = audit.file(value, digest, size, audit.relative(path), require_hash=True)
                if p:
                    hashed.add(audit.relative(p))
    ids, counts, source_ids = set(), collections.Counter(), set()
    for path in sorted(ROUND.glob('*cards.jsonl')):
        counts[path.name] += 0
        for row in audit.load(path):
            cid = pick(row, 'card_id', 'id')
            if not cid or cid in ids:
                audit.error('reading_card_id_missing_or_duplicate', str(cid))
            ids.add(cid)
            key = identity(row)
            associates = row.get('source_record_ids') or [key]
            if key not in sources or not isinstance(associates, list) or not set(associates).issubset(sources):
                audit.error('reading_card_unknown_source', str(cid))
            source_ids.update(x for x in associates if isinstance(x, str))
            if not pick(row, 'read_scope', 'reading_scope'):
                audit.error('reading_card_no_actual_scope', str(cid))
            if row.get('read_status') and row['read_status'] not in {'partial', 'full'}:
                audit.error('reading_card_status', str(cid))
            if not pick(row, 'limits', 'counterexamples_or_boundaries', 'limits_and_cannot_infer'):
                audit.error('reading_card_no_limits', str(cid))
            if not pick(row, 'interpretation_type', 'inference_status', 'implications_status'):
                audit.error('reading_card_inference_not_labelled', str(cid))
            if not pick(row, 'source_observation', 'method_or_argument', 'author_claim_paraphrase', 'direct_observations'):
                audit.error('reading_card_no_observation_or_argument', str(cid))
            evidence = pick(row, 'evidence', 'evidence_files', 'evidence_locator')
            if not evidence:
                audit.error('reading_card_missing_evidence', str(cid))
            check_local_evidence_paths(audit, evidence, 'reading card ' + str(cid))
            for value, digest, size in file_refs(evidence):
                p = audit.file(value, digest, size, str(cid), require_hash=True, require_size=True)
                if p:
                    hashed.add(audit.relative(p))
            # All explicitly named local raw files need a hash declaration in a
            # receipt/manifest/card; locator prose is not turned into a filename.
            for value in strings(evidence):
                if value.startswith(('.harness/', 'papers/')):
                    rel = locator_path(value)
                    # A manifest is a locator for the hashes checked above,
                    # not itself an unanchored scanned/source-original claim.
                    if Path(rel).suffix in {'.json', '.jsonl'}:
                        continue
                    if rel not in hashed and rel not in audit.hashed_files:
                        audit.error('card_evidence_without_hash_record', str(cid) + ': ' + rel)
            pages = row.get('printed_pages')
            if pages is not None and (not isinstance(pages, list) or not pages or
                                      any(not (type(n) is int and n >= 1) and
                                          not (isinstance(n, str) and re.fullmatch(r'(?:(?:preface|TOC|前言|目录)\s+)?[ivxlcdm]+', n, re.I))
                                          for n in pages)):
                audit.error('reading_card_invalid_printed_page', str(cid))
            counts[path.name] += 1
    audit.sections['reading'] = {
        'card_records': len(ids), 'by_file': dict(counts), 'source_records': sorted(source_ids),
        'manifests_with_hash_records': manifests, 'evidence_files_hash_checked': len(hashed),
        'limits': 'Named pages, local locators and evidence hashes are checked. Actual interpretation and complete-section claims require the separate manual readback.',
    }


def check_proposals(audit, sources, before):
    paths = sorted(set(ROUND.glob('*source-updates.jsonl')) | set(ROUND.glob('*source-proposals.jsonl'))
                   | set(ROUND.glob('*source-proposal.json')))
    fields, count = collections.defaultdict(set), 0
    for path in paths:
        loaded = audit.load(path)
        rows = loaded if isinstance(loaded, list) else [loaded]
        for row in rows:
            key = identity(row)
            if key not in sources:
                audit.error('proposal_source_not_found', audit.relative(path) + ': ' + str(key))
                continue
            updates = row.get('updates')
            if not isinstance(updates, dict) or not updates:
                audit.error('empty_or_unwrapped_source_proposal', str(key))
                continue
            count += 1
            for field, expected in updates.items():
                fields[key].add(field)
                if field not in sources[key] or not value_retained(expected, sources[key][field]):
                    audit.error('proposal_field_not_retained', key + ': ' + field + ' [' + path.name + ']')
            for field, expected in row.get('before', {}).items():
                if before.get(key, {}).get(field) != expected:
                    audit.error('proposal_before_not_frozen_value', key + ': ' + field)
            check_local_evidence_paths(audit, row.get('evidence'), 'source proposal ' + key)
    for key, old in before.items():
        if key not in sources:
            audit.error('baseline_source_removed', key)
            continue
        for field in ('id', 'title', 'authors', 'year', 'isbn', 'doi'):
            if old.get(field) != sources[key].get(field) and field not in fields[key]:
                audit.error('unproposed_bibliographic_drift', key + ': ' + field)
        # Access and reading must remain separate. Changing an old PDF path is
        # not an inevitable consequence of receiving a fuller HTML/body copy.
        for field in ('local_pdf',):
            if old.get(field) and old[field] != sources[key].get(field) and field not in fields[key]:
                audit.error('unproposed_existing_pdf_path_change', key)
    audit.sections['proposals'] = {
        'proposal_files': len(paths), 'proposals_checked': count,
        'fields_checked_by_record': {k: sorted(v) for k, v in fields.items()},
        'matching_is_static_not_semantic_proof': True,
    }


def pdf_pages(audit, path):
    try:
        result = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, timeout=30)
        match = re.search(r'^Pages:\s*(\d+)\s*$', result.stdout, re.M)
        if result.returncode or not match:
            audit.error('new_pdf_page_parse_failed', audit.relative(path))
            return None
        return int(match.group(1))
    except (OSError, subprocess.TimeoutExpired):
        audit.error('new_pdf_page_parser_unavailable', audit.relative(path))
        return None


def check_html_bundle(audit, receipt, context):
    path_value = pick(receipt, 'manifest_file', 'manifest_path', 'file', 'path')
    path = audit.path(path_value, context + ' manifest') if path_value else None
    if not path:
        audit.error('html_bundle_no_manifest_anchor', context)
        return None
    manifest = audit.load(path)
    if manifest.get('complete_book_body_html') is not True:
        audit.error('html_bundle_body_not_complete', context)
    expected = manifest.get('expected_chapters')
    if type(expected) is not int or expected < 1 or manifest.get('verified_chapters') != expected:
        audit.error('html_bundle_incomplete_chapter_coverage', context)
        expected = 0
    chapters = [str(item.get('label', '')) for item in manifest.get('files', [])
                if re.fullmatch(r'chapter-\d+', str(item.get('label', '')))]
    if len(chapters) != expected or {int(s.split('-')[1]) for s in chapters} != set(range(1, expected+1)):
        audit.error('html_bundle_actual_chapter_number_set', context)
    by_label = {item.get('label'):item for item in manifest.get('files', [])}
    labels = set(by_label)
    copyright_label = manifest.get('copyright_component_label', 'copyright')
    for label in ('introduction', copyright_label):
        if label not in labels:
            audit.error('html_bundle_required_part_missing', context + ': ' + label)
    # Collected volumes may put references at each chapter's end, unlike the
    # earlier two monographs. Require the declared set to close against every
    # numbered component except explicitly identified part introductions.
    if 'references' not in labels:
        structure = manifest.get('reference_structure', {})
        authored, part_intro = structure.get('chapter_labels'), structure.get('part_introduction_labels')
        if (structure.get('kind') != 'chapter_local_references' or not isinstance(authored,list)
                or not authored or len(authored)!=len(set(authored)) or not isinstance(part_intro,list)
                or len(part_intro)!=len(set(part_intro)) or set(authored)&set(part_intro)
                or set(authored)|set(part_intro)!=set(chapters)):
            audit.error('html_bundle_no_complete_reference_structure', context)
        else:
            for label in authored:
                item = by_label.get(label,{})
                body_path = audit.path(item.get('body_html'), context + ' chapter local references')
                body_text = body_path.read_text(errors='replace') if body_path and body_path.is_file() else ''
                headings = [match for match in re.finditer(r'<(p|h[1-6])\b[^>]*>(.*?)</\1>',body_text,re.S|re.I)
                            if re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',match.group(2)))).strip().casefold()
                            in {'references','works cited','bibliography'}]
                if not headings or not re.sub(r'<[^>]+>|\s+','',body_text[headings[-1].end():]):
                    audit.error('html_bundle_chapter_local_references_missing',context + ': ' + label)
    for value, digest, size in file_refs(manifest):
        audit.file(value, digest, size, context + ' bundle contents', require_hash=True)
    for item in manifest.get('files', []):
        if item.get('is_original_book_component') is False:
            if item.get('label') in set(chapters)|{'introduction',copyright_label,'references'}:
                audit.error('html_bundle_required_body_marked_as_platform_only',context + ': ' + str(item.get('label')))
            # Link-group pages and empty autogenerated index/glossary/license
            # placeholders are retained with source hashes, not counted as book
            # body. They do not invent a missing index or bibliography.
            continue
        body_value = item.get('body_html')
        body = audit.path(body_value, context) if body_value else None
        if not body or not body.is_file() or not re.sub(r'<[^>]+>|\s+', '', body.read_text(errors='replace')):
            audit.error('html_bundle_empty_or_missing_body', context + ': ' + str(item.get('label')))
    # This helper closes actual body image references against the inventory and
    # offline links and sums actual source-HTML/image bytes, not declared zeros.
    actual_bytes = _r4.check_bundle_images_and_source_bytes(audit, manifest, context)
    if not str(manifest.get('bytes_scope', '')).startswith(('original_html_plus_archived_book_images_only',
                                                          'sum_original_source_HTML_files_plus_archived_images_only')):
        audit.error('html_bundle_bytes_scope_missing', context)
    if manifest.get('bytes') != actual_bytes or receipt.get('bundle_total_bytes') != actual_bytes:
        audit.error('html_bundle_aggregate_bytes_drift', context)
    completeness = manifest.get('completeness_validation', {})
    if completeness.get('missing_substantive_components_detected') != []:
        audit.error('html_bundle_missing_substantive_components', context)
    # Count and labels alone cannot prove completeness. Archive a TOC/structure
    # observation with a hash; specific source interpretation is manually read.
    toc_refs = list(file_refs(manifest.get('toc_evidence', [])))
    if not toc_refs:
        audit.error('html_bundle_no_hashed_contents_evidence', context)
    for value, digest, size in toc_refs:
        audit.file(value, digest, size, context + ' contents evidence', require_hash=True, require_size=True)
    return manifest


def check_complete_chapter_pdf(audit, receipt, sources, context):
    """A complete native target chapter with its own references, including scans.

    Page maps may contain multiple printed leaves per physical PDF page. Require
    every target leaf, native figures/tables/layout and independently checked
    boundaries/references; a partial preview or plain transcription cannot pass
    merely by declaring complete_chapter_pdf.
    """
    start_errors = len(audit.errors)
    keys = receipt_sources(receipt)
    if len(keys) != 1 or any(sources.get(k, {}).get('type') not in {'chapter', 'book_chapter', 'book-chapter'} for k in keys):
        audit.error('complete_chapter_pdf_target_type', context)
        return set()
    key = next(iter(keys))
    if (receipt.get('complete_chapter_pdf') is not True or receipt.get('complete_chapter_body') is not True
            or receipt.get('complete_article') is not False or receipt.get('complete_book') is not False):
        audit.error('complete_chapter_pdf_flags', context)
    ref = receipt.get('chapter_body_verification')
    if not isinstance(ref, dict):
        audit.error('complete_chapter_pdf_no_independent_verification', context)
        return set()
    path = audit.file(pick(ref, 'file', 'path'), ref.get('sha256'), ref.get('bytes'),
                      context + ' independent complete chapter', require_hash=True, require_size=True)
    if not path:
        return set()
    proof = audit.load(path)
    if (identity(proof) != key or proof.get('target_type') != sources[key].get('type')
            or proof.get('verification_kind') != 'complete_original_chapter_pdf_with_own_references'):
        audit.error('complete_chapter_pdf_verification_identity', context)
    for flag in ('target_identity_verified', 'complete_chapter_body_verified',
                 'complete_chapter_references_verified', 'all_target_pages_present', 'substantive_components_verified'):
        if proof.get(flag) is not True:
            audit.error('complete_chapter_pdf_verification_flag', context + ': ' + flag)
    if proof.get('complete_book') is not False or not all(proof.get(k) for k in ('review_owner', 'read_scope', 'method', 'limits')):
        audit.error('complete_chapter_pdf_scope_or_limits', context)
    original = proof.get('source_pdf', {})
    original = original if isinstance(original, dict) else {}
    p = audit.file(pick(original, 'file', 'path'), original.get('sha256'), original.get('bytes'),
                   context + ' chapter PDF original', require_hash=True, require_size=True)
    if not p or p.suffix.lower() != '.pdf' or not p.read_bytes().startswith(b'%PDF-'):
        audit.error('complete_chapter_pdf_original', context)
        return set()
    count = pdf_pages(audit, p)
    if count is None or original.get('pages') != count:
        audit.error('complete_chapter_pdf_actual_page_count', context)
    pdf_refs = [(value,digest,size) for value,digest,size in file_refs(receipt) if Path(value).suffix.lower()=='.pdf']
    if (not pdf_refs or any(digest != original.get('sha256') for _,digest,_ in pdf_refs)
            or not any(audit.path(value,context)==p and digest==original.get('sha256') and size==original.get('bytes')
                       for value,digest,size in pdf_refs)):
        audit.error('complete_chapter_pdf_receipt_original_mismatch', context)
    target, mapping = proof.get('target_printed_pages'), proof.get('physical_page_coverage')
    if (not isinstance(target,list) or not target or not all(type(n) is int and n>0 for n in target)
            or target != list(range(target[0],target[-1]+1)) or not isinstance(mapping,list)
            or not mapping or not all(isinstance(row,dict) for row in mapping)):
        audit.error('complete_chapter_pdf_target_page_ranges', context)
        return set()
    physical = [row.get('physical_page') for row in mapping]
    printed, covered = [], []
    if (not all(type(n) is int and n>0 for n in physical) or len(set(physical)) != len(physical)
            or physical != list(range(physical[0],physical[-1]+1)) or count is None or physical[-1]>count):
        audit.error('complete_chapter_pdf_physical_mapping', context)
    for row in mapping:
        spread, selected = row.get('printed_pages'), row.get('target_printed_pages')
        if (not isinstance(spread,list) or not spread or not all(type(n) is int and n>0 for n in spread)
                or spread != list(range(spread[0],spread[-1]+1)) or not isinstance(selected,list)
                or selected != [n for n in spread if n in target] or not row.get('evidence')):
            audit.error('complete_chapter_pdf_printed_spread', context)
            continue
        printed.extend(spread)
        covered.extend(selected)
    if not printed or covered != target or len(printed)!=len(set(printed)) or printed != list(range(printed[0],printed[-1]+1)):
        audit.error('complete_chapter_pdf_target_leaf_coverage', context)
    if proof.get('excluded_neighbor_printed_pages',[]) != [n for n in printed if n not in target]:
        audit.error('complete_chapter_pdf_unexplained_neighbor_pages', context)
    refs = proof.get('target_reference_pages')
    if (not isinstance(refs,list) or not refs or not all(type(n) is int for n in refs)
            or refs != list(range(refs[0],target[-1]+1)) or not set(refs).issubset(target)):
        audit.error('complete_chapter_pdf_own_references_incomplete', context)
    boundary = proof.get('chapter_boundaries',{})
    boundary = boundary if isinstance(boundary,dict) else {}
    normalized = lambda value: re.sub(r'\W+','',str(value)).casefold()
    if (boundary.get('first_target_printed_page')!=target[0] or boundary.get('last_target_printed_page')!=target[-1]
            or not refs or boundary.get('reference_start_printed_page')!=refs[0]
            or not boundary.get('last_target_description')
            or normalized(boundary.get('verified_title'))!=normalized(sources[key].get('title'))
            or not any(normalized(boundary.get('verified_author'))==normalized(author) for author in sources[key].get('authors',[]))):
        audit.error('complete_chapter_pdf_title_author_or_boundaries',context)
    expected, components = proof.get('expected_substantive_component_ids'), proof.get('substantive_components')
    if (not isinstance(expected,list) or not expected or not all(isinstance(x,str) and x for x in expected)
            or len(expected)!=len(set(expected)) or not isinstance(components,list)
            or not all(isinstance(row,dict) for row in components) or len(components)!=len(expected)
            or {row.get('component_id') for row in components}!=set(expected)):
        audit.error('complete_chapter_pdf_substantive_components',context)
    else:
        for row in components:
            cp, pp = row.get('printed_pages'), row.get('physical_pages')
            if (not isinstance(cp,list) or not cp or not set(cp).issubset(target)
                    or not isinstance(pp,list) or not pp or not set(pp).issubset(physical)
                    or not row.get('visual_scope') or not row.get('evidence')
                    or any(not any(n in mapped.get('target_printed_pages',[]) and mapped.get('physical_page') in pp
                                   for mapped in mapping) for n in cp)):
                audit.error('complete_chapter_pdf_component_scope',context + ': ' + str(row.get('component_id')))
    for value,digest,size in file_refs(proof):
        audit.file(value,digest,size,context + ' native chapter verification evidence',require_hash=True,require_size=True)
    return keys if len(audit.errors)==start_errors else set()


def check_complete_chapter_body(audit, receipt, sources, context):
    """Narrow PDF chapter-body case; never promote a partial book or transcription.

    A complete target chapter may precede a bibliography shared by the whole
    book. Its missing shared bibliography remains an explicit separate gap.
    The acquiring branch's flag alone is insufficient: require an independently
    hashed verification of identity, every body page, all substantive figures
    and the actual chapter boundaries.
    """
    start_errors = len(audit.errors)
    keys = receipt_sources(receipt)
    if len(keys) != 1 or any(sources.get(k, {}).get('type') not in {'chapter', 'book_chapter', 'book-chapter'} for k in keys):
        audit.error('chapter_body_target_is_not_single_chapter', context)
        return set()
    key = next(iter(keys))
    if receipt.get('complete_book') is not False or receipt.get('complete_article') is not False:
        audit.error('chapter_body_overbroad_completion_flags', context)
    ref = receipt.get('chapter_body_verification')
    if not isinstance(ref, dict):
        audit.error('chapter_body_no_independent_verification_anchor', context)
        return set()
    p = audit.file(pick(ref, 'file', 'path'), ref.get('sha256'), ref.get('bytes'),
                   context + ' independent chapter verification', require_hash=True, require_size=True)
    if not p:
        return set()
    proof = audit.load(p)
    if identity(proof) != key or proof.get('target_type') != sources[key].get('type'):
        audit.error('chapter_body_verification_identity', context)
    for flag in ('target_identity_verified', 'complete_chapter_body_verified',
                 'all_chapter_body_pages_present', 'all_key_figures_present', 'substantive_components_verified'):
        if proof.get(flag) is not True:
            audit.error('chapter_body_verification_flag_missing', context + ': ' + flag)
    if proof.get('complete_book') is not False or not proof.get('review_owner') or not proof.get('read_scope') or not proof.get('limits'):
        audit.error('chapter_body_verification_scope_or_limits', context)
    original = proof.get('source_pdf', {})
    original_path = audit.file(pick(original, 'file', 'path'), original.get('sha256'), original.get('bytes'),
                               context + ' chapter PDF', require_hash=True, require_size=True)
    if not original_path or original_path.suffix.lower() != '.pdf':
        audit.error('chapter_body_original_not_pdf', context)
        return set()
    pdf_refs = [(value, digest, size) for value, digest, size in file_refs(receipt) if Path(value).suffix.lower() == '.pdf']
    if (not pdf_refs or any(digest != original.get('sha256') for _, digest, _ in pdf_refs)
            or not any(audit.path(value, context) == original_path and digest == original.get('sha256')
                       and size == original.get('bytes') for value, digest, size in pdf_refs)):
        audit.error('chapter_body_receipt_original_mismatch', context)
    physical, printed = proof.get('physical_body_pages'), proof.get('printed_body_pages')
    valid_pages = lambda values: isinstance(values, list) and bool(values) and all(type(n) is int and n > 0 for n in values) and values == list(range(values[0], values[-1]+1))
    if not valid_pages(physical) or not valid_pages(printed) or len(physical) != len(printed):
        audit.error('chapter_body_page_ranges_not_complete', context)
        return set()
    actual_pages = pdf_pages(audit, original_path)
    if original.get('pages') != actual_pages or actual_pages is None or physical[-1] > actual_pages:
        audit.error('chapter_body_physical_range_outside_pdf', context)
    continuity = proof.get('body_page_continuity', [])
    if (len(continuity) != len(physical)
            or [(r.get('physical_page'), r.get('printed_page_observed')) for r in continuity] != list(zip(physical, printed))
            or any(type(r.get('nonwhitespace_characters')) is not int or r['nonwhitespace_characters'] <= 0 for r in continuity)):
        audit.error('chapter_body_actual_page_continuity', context)
    boundary = proof.get('chapter_boundaries', {})
    normalized = lambda value: re.sub(r'\W+', '', str(value)).casefold()
    if (boundary.get('first_physical_page') != physical[0] or boundary.get('last_physical_page') != physical[-1]
            or type(boundary.get('next_chapter_physical_page')) is not int
            or boundary['next_chapter_physical_page'] <= physical[-1]
            or actual_pages is None or boundary['next_chapter_physical_page'] > actual_pages
            or not boundary.get('last_body_description')
            or normalized(boundary.get('verified_title')) != normalized(sources[key].get('title'))
            or not any(normalized(boundary.get('verified_author')) == normalized(author) for author in sources[key].get('authors', []))):
        audit.error('chapter_body_title_author_or_boundaries', context)
    expected, figures = proof.get('expected_figure_ids'), proof.get('figures')
    if (not isinstance(expected, list) or not isinstance(figures, list)
            or not all(isinstance(item, str) and item for item in expected)
            or not all(isinstance(item, dict) for item in figures)
            or len(expected) != len(set(expected)) or len(figures) != len(expected)
            or {r.get('figure_id') for r in figures} != set(expected)
            or any(r.get('physical_page') not in physical or not r.get('visual_scope') or not r.get('evidence') for r in figures)):
        audit.error('chapter_body_missing_figure_or_visual_check', context)
    gap = proof.get('outside_chapter_reference_gap')
    if (not isinstance(gap, dict) or gap.get('kind') != 'shared_book_bibliography_outside_target_chapter'
            or gap.get('obtained') is not False or gap.get('exact_last_reference_page_visually_verified') is not False
            or type(gap.get('bibliography_starts_printed_page')) is not int
            or gap['bibliography_starts_printed_page'] <= printed[-1]
            or type(gap.get('following_author_index_starts_printed_page')) is not int
            or gap['following_author_index_starts_printed_page'] <= gap['bibliography_starts_printed_page']
            or gap.get('inferred_upper_bound_before_following_section') != gap['following_author_index_starts_printed_page']-1
            or not gap.get('scope') or receipt.get('outside_chapter_reference_gap') != gap
            or receipt.get('shared_book_bibliography_obtained') is not False):
        audit.error('chapter_body_unrecorded_outside_reference_gap', context)
    for value, digest, size in file_refs(proof):
        audit.file(value, digest, size, context + ' independent chapter evidence', require_hash=True, require_size=True)
    return keys if len(audit.errors) == start_errors else set()


def check_acquisition(audit, sources, before, frozen, statuses, old_pdfs):
    old = {row['path']: row for row in old_pdfs}
    pdfs = audit.load(BASE / 'acquisition/pdf-files.jsonl')
    current = {row.get('path'): row for row in pdfs}
    if len(current) != len(pdfs):
        audit.error('duplicate_current_pdf_path', 'registry paths are not unique')
    for value, row in old.items():
        audit.file(value, row.get('sha256'), row.get('bytes'), 'frozen existing PDF',
                   require_hash=True, require_size=True)
        if value not in current or any(row.get(k) != current[value].get(k) for k in ('sha256', 'bytes', 'pages')):
            audit.error('existing_pdf_registry_drift', value)
    new = [row for value, row in current.items() if value not in old]
    new_paths = {row.get('path') for row in new}
    old_hashes = {row.get('sha256') for row in old.values()}
    duplicate_old_content = [row.get('path') for row in new if row.get('sha256') in old_hashes]
    if duplicate_old_content:
        audit.warn('new_pdf_path_reuses_existing_content_hash', repr(sorted(duplicate_old_content)))
    records, refs_seen, books, articles, chapters = [], set(), set(), set(), set()
    access_count, existing_count, bundle_keys = 0, 0, set()
    receipt_files = sorted(ROUND.glob('*receipts.jsonl'))
    for path in receipt_files:
        for row in audit.load(path):
            # Expanded manifests describe an already anchored package. They are
            # verified below against its current manifest rather than counted.
            if row.get('format') == 'html_bundle' and row.get('expected_chapters') and not pick(row, 'file', 'manifest_path', 'manifest_file', 'path'):
                continue
            records.append((path, row))
    child_files = set()
    for path, row in list(records):
        for value in strings(row):
            if value.startswith('papers/') and value.endswith('/receipt.json'):
                child = audit.path(value, 'referenced detailed receipt')
                if child and child not in child_files:
                    child_files.add(child)
                    records.append((child, audit.load(child)))
    # A newly registered supplemental PDF may be outside the frozen62. Only
    # select its explicit new path from the global receipt log; never count all
    # historical CNKI records as this round's acquisitions.
    for row in audit.load(BASE / 'acquisition/cnki-receipts.jsonl', required=False):
        if any(value in new_paths for value, _, _ in file_refs(row)):
            normalized = dict(row)
            if not receipt_sources(normalized):
                matches = [key for key in sources if key.rsplit(':', 1)[-1] == row.get('id')]
                if len(matches) == 1:
                    normalized['source_records'] = matches
            records.append((BASE / 'acquisition/cnki-receipts.jsonl', normalized))
    for path, row in records:
        context = path.name + ': ' + str(identity(row) or row.get('id'))
        associations = receipt_sources(row)
        if not associations or not associations.issubset(sources):
            audit.error('receipt_source_identity', context)
        refs = list(file_refs(row))
        if not refs:
            attempts = pick(row, 'attempts', 'round6_attempts')
            if attempts:
                access_count += 1
                check_local_evidence_paths(audit, attempts, context)
            else:
                audit.error('receipt_no_hashed_files_or_attempts', context)
        for value, digest, size in refs:
            p = audit.file(value, digest, size, context, require_hash=True, require_size=True)
            if p:
                refs_seen.add(audit.relative(p))
        if row.get('new_acquisition') is False or row.get('new_pdf_obtained') is False:
            existing_count += 1
        if row.get('format') == 'html_bundle':
            key = (row.get('id'), tuple(sorted(associations)))
            if key not in bundle_keys:
                bundle_keys.add(key)
                manifest = check_html_bundle(audit, row, context)
                if manifest and complete_book_receipt(manifest):
                    books.update(associations)
        elif complete_book_receipt(row):
            books.update(associations)
        if row.get('complete_chapter_pdf') is True:
            chapters.update(check_complete_chapter_pdf(audit, row, sources, context))
        elif row.get('complete_chapter_body') is True:
            chapters.update(check_complete_chapter_body(audit, row, sources, context))
        extent = str(row.get('document_extent', '')).lower()
        partial_extent = any(word in extent for word in ('sample', 'preview', 'frontmatter', 'preface_only', 'abstract_only'))
        # A format label says how a file is stored, not how much of the target
        # article it contains. Require an explicit completeness declaration and
        # a real hashed artifact; closure also needs manual readback below.
        if row.get('complete_article') is True:
            if partial_extent or not refs:
                audit.error('article_complete_flag_without_complete_artifact', context)
            else:
                articles.update(associations)
        if any(word in extent for word in ('sample', 'preview', 'frontmatter', 'preface_only')) and row.get('complete_book') is True:
            audit.error('sample_claimed_as_complete_book', context)
    for path in receipt_files:
        for snapshot in audit.load(path):
            if snapshot.get('format') != 'html_bundle' or not snapshot.get('expected_chapters') or pick(snapshot, 'file', 'manifest_path', 'manifest_file', 'path'):
                continue
            anchors = [row for _, row in records if row.get('format') == 'html_bundle'
                       and row.get('id') == snapshot.get('id') and receipt_sources(row) == receipt_sources(snapshot)]
            if not anchors:
                audit.error('expanded_bundle_no_anchor', path.name)
            for anchor in anchors:
                p = audit.path(pick(anchor, 'file', 'manifest_path', 'manifest_file', 'path'), 'bundle snapshot anchor')
                if not p or audit.load(p) != snapshot:
                    audit.error('expanded_bundle_snapshot_drift', path.name)
    for row in new:
        value = row.get('path')
        p = audit.file(value, row.get('sha256'), row.get('bytes'), 'new registered PDF',
                       require_hash=True, require_size=True)
        if p:
            if not p.read_bytes().startswith(b'%PDF-'):
                audit.error('new_pdf_magic', value)
            pages = pdf_pages(audit, p)
            if pages is not None and row.get('pages') != pages:
                audit.error('new_pdf_page_count', value)
        if value not in refs_seen:
            audit.error('new_pdf_without_round6_receipt', str(value))
        if not row.get('source_records') or not set(row['source_records']).issubset(sources):
            audit.error('new_pdf_source_association', str(value))
    pending = unique_rows(audit, audit.load(BASE / 'acquisition/pending-access.jsonl'), 'current pending queue')
    reading_queue = unique_rows(audit, audit.load(BASE / 'acquisition/reading-queue.jsonl'), 'current reading queue')
    overlap = set(pending) & set(reading_queue)
    if overlap:
        audit.error('generated_pending_and_reading_queues_overlap', repr(sorted(overlap)))
    if (set(pending) | set(reading_queue)) - set(sources):
        audit.error('generated_queue_unknown_source', repr(sorted((set(pending) | set(reading_queue)) - set(sources))))
    cleared = set(frozen) - set(pending)
    for key in cleared:
        complete = books if frozen[key].get('type') in BOOK_TYPES else articles | chapters
        if key not in complete:
            audit.error('frozen_queue_cleared_without_complete_body_receipt', key)
    new_complete_book_flags = set()
    new_complete_chapter_flags = set()
    for key, source in sources.items():
        if source.get('full_book_obtained') is True and before.get(key, {}).get('full_book_obtained') is not True:
            new_complete_book_flags.add(key)
            if key not in books:
                audit.error('new_full_book_flag_without_complete_body_receipt', key)
            if key in pending:
                audit.error('new_complete_book_body_still_missing_in_queue', key)
        if source.get('complete_chapter_body') is True and before.get(key, {}).get('complete_chapter_body') is not True:
            new_complete_chapter_flags.add(key)
            if key not in chapters:
                audit.error('new_complete_chapter_flag_without_verified_body_receipt', key)
            if key in pending:
                audit.error('new_complete_chapter_body_still_missing_in_queue', key)
    for key, status in statuses.items():
        if status.get('fulltext_gap_closed') is True and key in pending:
            audit.error('status_closed_but_body_queue_pending', key)
    audit.sections['acquisition'] = {
        'receipt_files': len(receipt_files), 'receipt_records_with_unique_file_anchors_or_attempts': len(records),
        'access_receipt_records': access_count, 'existing_source_reading_receipts': existing_count,
        'frozen_existing_pdf_paths': len(old), 'new_registered_pdfs': len(new),
        'new_pdf_count_scope': 'New registered physical paths; not necessarily new content, full works or independent sources',
        'new_pdf_unique_hashes_not_in_baseline': len({row.get('sha256') for row in new}-old_hashes),
        'new_pdf_paths_reusing_baseline_hash': sorted(duplicate_old_content),
        'new_pdf_pages': sum(r.get('pages', 0) for r in new), 'new_pdf_bytes': sum(r.get('bytes', 0) for r in new),
        'html_book_bundles': len(bundle_keys), 'complete_book_body_records': sorted(books),
        'newly_marked_complete_book_records': sorted(new_complete_book_flags),
        'complete_chapter_body_records': sorted(chapters),
        'newly_marked_complete_chapter_body_records': sorted(new_complete_chapter_flags),
        'complete_article_records': sorted(articles),
        'frozen_ids_cleared_from_file_queue': sorted(cleared),
        'frozen_ids_remaining_in_file_queue': sorted(set(frozen) & set(pending)),
        'new_pending_identities_outside_frozen_scope': sorted(set(pending)-set(frozen)),
        'current_pending_total': len(pending),
        'current_reading_queue_total': len(reading_queue),
        'generated_queue_identity_overlap': sorted(overlap),
        'note': 'Route investigation, full-body acquisition, native format and reading extent remain separate. Existing-source rereading is not a new acquisition.',
    }
    return [row for _, row in records], pdfs


def check_global_summary(audit, sources, pdfs):
    result = audit.load(BASE / 'validation.json')
    if result.get('passed') is not True:
        audit.error('global_delivery_validation_not_passed', 'validation.json')
    observed = {
        'source_records': len(sources), 'pdf_files': len(pdfs),
        'physical_pdf_pages': sum(row.get('pages', 0) for row in pdfs),
        'bytes': sum(row.get('bytes', 0) for row in pdfs),
        'reading_status': dict(collections.Counter(row.get('read_status') for row in sources.values())),
    }
    for field, expected in observed.items():
        if result.get(field) != expected:
            audit.error('global_validation_stale_or_count_drift', field)
    audit.sections['global_delivery'] = {'passed_flag': result.get('passed'), **observed,
                                        'upstream_package_warnings': result.get('warnings', []),
                                        'pdf_files_with_parser_warnings': sum(bool(row.get('parser_warnings')) for row in pdfs),
                                        'scope': 'Counts independently recomputed here; global validator owns link/catalog completeness'}


def check_round6_summary_and_merge_log(audit, sources, before):
    summary = audit.load(ROUND / 'summary.json')
    acquisition, reading = audit.sections['acquisition'], audit.sections['reading']
    expected = {
        'frozen_baseline': 62, 'frozen_chinese': 26, 'frozen_international_and_other': 36,
        'baseline_pdf_files': 102, 'closed_baseline_records': len(acquisition['frozen_ids_cleared_from_file_queue']),
        'retained_baseline_records': len(acquisition['frozen_ids_remaining_in_file_queue']),
        'closed_baseline_ids': acquisition['frozen_ids_cleared_from_file_queue'],
        'retained_baseline_ids': acquisition['frozen_ids_remaining_in_file_queue'],
        'new_pending_ids': acquisition['new_pending_identities_outside_frozen_scope'],
        'current_pending_records': acquisition['current_pending_total'],
        'current_available_reading_records': acquisition['current_reading_queue_total'],
        'generated_queue_identity_overlap': acquisition['generated_queue_identity_overlap'],
        'new_pdf_files': acquisition['new_registered_pdfs'],
        'new_pdf_pages': acquisition['new_pdf_pages'], 'new_pdf_bytes': acquisition['new_pdf_bytes'],
        'new_pdf_unique_hashes_not_in_baseline': acquisition['new_pdf_unique_hashes_not_in_baseline'],
        'analysis_cards': reading['card_records'], 'analysis_cards_by_file': reading['by_file'],
        'current_source_records': len(sources),
        'current_read_status': dict(collections.Counter(row.get('read_status') for row in sources.values())),
        'new_source_records': sorted(set(sources)-set(before)),
        'new_complete_chapter_body_records': acquisition['newly_marked_complete_chapter_body_records'],
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            audit.error('round6_summary_drift', field)
    def source_digest(row):
        return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    log = unique_rows(audit, audit.load(ROUND / 'source-merge-log.jsonl'), 'round6 merge log')
    actual_changes = {key for key, row in sources.items() if row != before.get(key)}
    if set(log) != actual_changes:
        audit.error('merge_log_changed_identity_scope', repr(sorted(set(log)^actual_changes)))
    for key, record in log.items():
        if key not in sources:
            continue
        old, current = before.get(key), sources[key]
        changes = sorted(field for field in set(old or {}) | set(current)
                         if (old or {}).get(field) != current.get(field))
        if (record.get('before_sha256') != (source_digest(old) if old else None)
                or record.get('after_sha256') != source_digest(current)
                or record.get('changed_fields') != changes
                or record.get('new_record') is not (old is None)):
            audit.error('source_merge_log_field_or_hash_drift', key)
    audit.sections['round6_summary'] = {'fields_checked': sorted(expected),
                                       'changed_source_records': len(actual_changes),
                                       'merge_log_records': len(log)}


def check_manual_readback(audit, final=False, cleared=()):
    path = PRIVATE / 'independent-review/readback.json'
    record = audit.load(path)
    findings = record.get('findings', [])
    targets = record.get('target_file_sha256', [])
    if not findings or not targets or not record.get('method') or not record.get('limits'):
        audit.error('independent_manual_readback_incomplete', audit.relative(path))
    if final and record.get('phase') != 'final_independent_readback_after_integration':
        audit.error('manual_readback_not_final_after_integration', audit.relative(path))
    for target in targets:
        audit.file(target.get('path'), target.get('sha256'), context='independent readback target', require_hash=True)
    domains = set()
    for finding in findings:
        for field in ('id', 'status', 'issue', 'resolution'):
            if not finding.get(field):
                audit.error('manual_finding_missing_field', str(finding.get('id')) + ': ' + field)
        domains.update(finding.get('domains', []))
        if final and finding.get('requires_correction') is True and finding.get('correction_resolved') is not True:
            audit.error('manual_semantic_correction_unresolved', str(finding.get('id')))
        if final and finding.get('peer_receipt_pending') is True:
            audit.error('self_authored_comparison_peer_receipt_pending', str(finding.get('id')))
        check_local_evidence_paths(audit, finding.get('evidence', []), 'manual finding ' + str(finding.get('id')))
        for value, digest, size in file_refs(finding.get('evidence', [])):
            audit.file(value, digest, size, 'manual original-page evidence',
                       require_hash=True, require_size=True)
    if not {'chinese', 'international'}.issubset(domains):
        audit.error('manual_readback_lacks_both_branches', repr(sorted(domains)))
    checked_closures = set()
    for closure in record.get('fulltext_closure_checks', []):
        key = identity(closure)
        if (closure.get('target_identity_verified') is True
                and closure.get('complete_target_body_verified') is True
                and closure.get('scope_and_limits') and closure.get('evidence')):
            checked_closures.add(key)
        else:
            audit.error('manual_complete_body_check_incomplete', str(key))
        check_local_evidence_paths(audit, closure.get('evidence', []), 'fulltext closure original evidence')
        for value, digest, size in file_refs(closure.get('evidence', [])):
            audit.file(value, digest, size, 'manual complete-body evidence', require_hash=True, require_size=True)
    if set(cleared) - checked_closures:
        audit.error('queue_closure_without_manual_body_identity_check', repr(sorted(set(cleared)-checked_closures)))
    audit.sections['manual_readback'] = {'method': record.get('method'), 'findings': findings,
                                        'target_files_hash_checked': len(targets),
                                        'fulltext_closures_manually_checked': sorted(checked_closures),
                                        'limits': record.get('limits')}


def check_public_content(audit, receipts):
    binaries = [audit.relative(p) for p in BASE.rglob('*') if p.is_file() and p.suffix.lower() in _r4.RESTRICTED_SUFFIXES]
    if binaries:
        audit.error('raw_originals_or_scans_in_public_docs', repr(binaries))
    public_texts = {}
    for path in ROUND.rglob('*'):
        if path.suffix not in {'.md', '.json', '.jsonl'}:
            continue
        text = path.read_text()
        public_texts[path] = re.sub(r'\s+', '', text)
        for match in re.finditer(r'https?://[^\s<>"\)]+', text):
            try:
                keys = {k.lower() for k, _ in parse_qsl(urlsplit(match.group()).query)}
            except ValueError:
                continue
            if keys & _r4.SENSITIVE_QUERY_KEYS:
                audit.error('signed_or_session_query_in_public_docs', audit.relative(path) + ': query keys ' + repr(sorted(keys & _r4.SENSITIVE_QUERY_KEYS)))
    raw_paths = set(PRIVATE.rglob('*.txt'))
    for row in receipts:
        for value in strings(row):
            if value.startswith(('papers/', '.harness/')) and value.endswith(('.txt', '.html')):
                p = audit.path(value, 'private text copy screen')
                if p and p.is_file():
                    raw_paths.add(p)
    hits = []
    for raw in sorted(raw_paths):
        if raw.stat().st_size > 20_000_000:
            audit.warn('large_raw_copy_screen_skipped', audit.relative(raw))
            continue
        text = re.sub(r'\s+', '', raw.read_text(errors='replace'))
        for offset in range(0, max(0, len(text)-499), 250):
            segment = text[offset:offset+500]
            hit = next((p for p, public in public_texts.items() if segment in public), None)
            if hit:
                hits.append({'public': audit.relative(hit), 'private': audit.relative(raw)})
                break
    if hits:
        audit.error('long_exact_raw_text_in_public_round6_docs', repr(hits))
    audit.sections['public_content'] = {'public_binary_originals_or_scans': binaries,
        'round6_text_files_screened': len(public_texts), 'private_text_files_screened': len(raw_paths),
        'long_exact_raw_text_hits': hits,
        'limits': 'Binaries, signed-query keys and exact 500-character runs only; not a complete quotation/copyright judgement'}


def report_markdown(result):
    checks = result['checks']
    scope, reading, acq = (checks[k] for k in ('frozen_scope', 'reading', 'acquisition'))
    lines = ['# 第六轮独立验收', '',
             '结果：' + ('通过' if result['passed'] else '未通过') + '。身份、终态、字段、原件及散列的静态检查，与原页人工抽审分别记录；通过不证明全文全部取得或编辑效果。', '',
             '| 检查对象 | 结果 |', '|---|---|',
             '| 冻结基线 | 62项：中文26、国际及其余36；102份既有PDF按冻结路径和散列核对 |',
             f'| 路线调查终态 | {scope["terminal_investigations"]}/62；身份一致={scope["identities_match"]} |',
             f'| 阅读卡 | {reading["card_records"]}张；按实际产出核验，没有预定数量门槛 |',
             f'| 新注册PDF | {acq["new_registered_pdfs"]}份，{acq["new_pdf_pages"]}页；原件大小、散列、magic、页数及回执关联 |',
             f'| 原冻结缺口 | 闭合{len(acq["frozen_ids_cleared_from_file_queue"])}，仍缺{len(acq["frozen_ids_remaining_in_file_queue"])}；本轮调查结束不等于全部获取 |',
             '| 运行时 | skills/commands/plugin/scripts/evals相对HEAD差异单列于JSON |', '',
             '## 原文抽审、修正和保留边界', '']
    for f in checks['manual_readback']['findings']:
        lines += ['- `' + f['id'] + '`（' + f['status'] + '）：' + f['issue'] + ' ' + f['resolution']]
    lines += ['', '## 静态错误', '']
    lines += ['- `' + e['code'] + '`：' + e['detail'] for e in result['errors']] or ['无。']
    lines += ['', '## 额外告警', '']
    lines += ['- `' + e['code'] + '`：' + e['detail'] for e in result['warnings']] or ['无额外静态告警。']
    lines += ['', '本工具不改来源、目录、获取队列或运行时，也不重写第四、五轮历史验收。结构化明细见[JSON](review-final-round6.json)。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final', action='store_true', help='write round6 final review only after integration confirmation')
    args = parser.parse_args()
    audit = Audit()
    frozen, old_pdfs = check_baseline(audit)
    sources, before = source_map(audit, BASE), source_map(audit, FROZEN)
    statuses = check_statuses(audit, sources, frozen)
    receipts, pdfs = check_acquisition(audit, sources, before, frozen, statuses, old_pdfs)
    check_manifests_and_reading(audit, sources)
    check_proposals(audit, sources, before)
    check_global_summary(audit, sources, pdfs)
    check_round6_summary_and_merge_log(audit, sources, before)
    _r4.check_protected_runtime(audit)
    check_manual_readback(audit, final=args.final,
                          cleared=set(audit.sections['acquisition']['frozen_ids_cleared_from_file_queue'])
                                  | set(audit.sections['acquisition']['newly_marked_complete_book_records'])
                                  | set(audit.sections['acquisition']['newly_marked_complete_chapter_body_records']))
    check_public_content(audit, receipts)
    result = {'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'phase': 'final_after_integration' if args.final else 'read_only_preflight',
              'passed': not audit.errors, 'checks': audit.sections,
              'unique_files_hash_checked': len(audit.hashed_files),
              'errors': audit.errors, 'warnings': audit.warnings,
              'scope': 'Round6 frozen62/status62, actual reading, proposals, raw-file receipts, manual interpretation audit and runtime restrictions; not exhaustiveness or editing effectiveness'}
    if args.final:
        (BASE / 'review-final-round6.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        (BASE / 'review-final-round6.md').write_text(report_markdown(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
