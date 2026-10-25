#!/usr/bin/env python3
"""Validate round 4's saved scope and evidence, independently of the builders.

Run after integration, with ``--final`` to write review-final-round4.{md,json}.
Without that flag this is read-only and prints its result.  No network access,
source-card edits, acquisition, queue rebuilding, or skill changes occur here.
Static agreement is not proof of a source's truth or an editing method's effect.
"""
import argparse
import collections
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-20-human-expression'
PRIVATE = ROOT / '.harness/research-20261020/round4'
FROZEN = PRIVATE / 'baseline'
BASELINE_SHA256 = '855a0fc864e49cbcec2ebeaed0f294aeb9aaa5dcbf2c69c1b5d060a529536aa5'
HISTORICAL_PDF_AUDIT_SHA256 = '8485d6430a6e8aa10282e754d4a3250a13e6a6328026724a11956d81aba7e26e'
BOOK_TYPES = {'book', 'edited_book', 'edited-book', 'open_book'}
PENDING_STATES = {'pending', 'in_progress', 'not_yet_reviewed',
                  'in_progress_not_yet_reviewed', 'new_route_investigation_pending'}
TERMINAL_STATES = {
    'acquired_complete_transcription', 'verified_online_full_book',
    'preview_or_bibliography_only', 'login_or_platform_blocked',
    'no_legal_fulltext_found', 'delegated_same_work_route',
    'complete_article_pdf_obtained',
    'complete_book_pdf_obtained',
    'complete_book_body_html_obtained_original_pdf_pending',
    'partial_material_obtained_fulltext_pending',
    'new_routes_checked_fulltext_pending', 'manual_verification_handoff',
    'school_catalog_no_fulltext_control', 'prior_online_full_book_preserved',
    'prior_online_alternate_edition_preserved', 'prior_online_full_book_deep_read',
    'official_author_archive_metadata_only', 'new_route_access_gap',
    'acquired_complete_article_transcription',
    'school_catalog_translation_and_original_kept_separate',
    'author_institution_no_fulltext_found', 'school_online_late_chapters_verified',
    'institution_route_not_completed_no_fulltext',
    'existing_legal_chapter_only_no_new_fullbook',
    'publisher_metadata_no_open_book_found',
    'target_preview_and_alternate_reader_opened',
    'additional_platform_chapter1_only_verified',
}
CLASSIC_REQUIRED = ('ZH008', 'ZH010', 'ZH072')
PAGE_LIMITS = {'ZH008': 525, 'ZH010': 238, 'ZH072': 619, 'ZH079': 261}
RESTRICTED_SUFFIXES = {'.pdf', '.epub', '.png', '.jpg', '.jpeg', '.webp',
                       '.gif', '.tiff', '.tif', '.djvu', '.pdg', '.caj'}
PROTECTED_PATHS = ('skills', 'commands', '.claude-plugin', 'scripts', 'evals')
SENSITIVE_QUERY_KEYS = {'token', 'access_token', 'session', 'sessionid',
                        'jsessionid', 'signature', 'ticket', 'auth', 'enc', 'ucode'}


class Audit:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.file_cache = {}
        self.hashed_files = {}
        self.file_pages = {}
        self.sections = {}

    def error(self, code, detail):
        self.errors.append({'code': code, 'detail': detail})

    def warn(self, code, detail):
        self.warnings.append({'code': code, 'detail': detail})

    def relative(self, path):
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return '<outside-workspace>'

    def path(self, value, context):
        if not isinstance(value, str) or not value or value.startswith(('http:', 'https:')):
            self.error('invalid_local_path', context)
            return None
        p = (Path(value) if value.startswith('/') else ROOT / value).resolve()
        if not p.is_relative_to(ROOT):
            self.error('path_outside_workspace', context)
            return None
        return p

    def load(self, path, required=True):
        if not path.is_file():
            if required:
                self.error('missing_file', self.relative(path))
            return [] if path.suffix == '.jsonl' else {}
        try:
            if path.suffix == '.jsonl':
                return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
            return json.loads(path.read_text())
        except (ValueError, UnicodeError) as exc:
            self.error('invalid_json', self.relative(path) + ': ' + str(exc))
            return [] if path.suffix == '.jsonl' else {}

    def file(self, value, digest=None, size=None, context='', require_hash=False,
             require_size=False):
        p = self.path(value, context)
        if p is None:
            return None
        if not p.is_file():
            self.error('missing_evidence_file', self.relative(p) + ' [' + context + ']')
            return None
        if p not in self.file_cache:
            data = p.read_bytes()
            self.file_cache[p] = (hashlib.sha256(data).hexdigest(), len(data))
        actual_sha, actual_size = self.file_cache[p]
        if require_hash and not digest:
            self.error('missing_hash', self.relative(p) + ' [' + context + ']')
        if digest and digest != actual_sha:
            self.error('hash_drift', self.relative(p) + ' [' + context + ']')
        if require_size and type(size) is not int:
            self.error('missing_size', self.relative(p) + ' [' + context + ']')
        if size is not None and size != actual_size:
            self.error('size_drift', self.relative(p) + ' [' + context + ']')
        if digest:
            self.hashed_files[self.relative(p)] = actual_sha
        return p


def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def source_map(audit, base):
    result = {}
    for path in sorted(base.glob('*/sources.jsonl')):
        for row in audit.load(path):
            key = path.parent.name + ':' + str(row.get('id', ''))
            if key in result:
                audit.error('duplicate_source_id', key)
            result[key] = row
    if base == FROZEN:
        for row in audit.load(base / 'catalog.jsonl'):
            key = row.get('record_id')
            if key and key not in result:
                result[key] = {**row, 'id': row.get('source_id')}
    return result


def identity(row):
    return row.get('record_id') or row.get('source_record_id') or row.get('parent_record_id')


def check_local_evidence_paths(audit, value, context):
    for text in strings(value):
        if text.startswith(('.harness/', 'papers/', 'docs/', str(ROOT) + '/')):
            path = re.sub(r':\d+(?:[-–]\d+)?$', '', text.split('#', 1)[0])
            audit.file(path, context=context)


def unique_rows(audit, rows, label):
    result = {}
    for row in rows:
        key = identity(row)
        if not key and isinstance(row.get('id'), str):
            if ':' in row['id']:
                key = row['id']
            elif label == 'chinese-status.jsonl' and row['id'].startswith('ZH'):
                key = 'linguistics-zh:' + row['id']
        if not key:
            audit.error('missing_record_id', label)
            continue
        if key in result:
            audit.error('duplicate_status_id', label + ': ' + key)
        result[key] = row
    return result


def check_frozen_and_status(audit, sources):
    path = FROZEN / 'acquisition/pending-access.jsonl'
    audit.file(str(path), BASELINE_SHA256, context='immutable frozen 65 IDs')
    frozen = unique_rows(audit, audit.load(path), 'frozen baseline')
    zh = {key for key in frozen if key.startswith('linguistics-zh:')}
    other = set(frozen) - zh
    if len(frozen) != 65 or len(zh) != 24 or len(other) != 41:
        audit.error('frozen_scope_drift', 'expected 65 = ZH24 + other41')
    statuses = {}
    terminal = []
    status_counts = collections.Counter()
    for name, expected in (('chinese-status.jsonl', zh), ('international-status.jsonl', other)):
        rows = unique_rows(audit, audit.load(BASE / 'fulltext-round4' / name), name)
        if set(rows) != expected:
            audit.error('status_scope_mismatch', name + ': missing=' + repr(sorted(expected-set(rows)))
                        + '; extra=' + repr(sorted(set(rows)-expected)))
        for key, row in rows.items():
            statuses[key] = row
            if key not in sources:
                audit.error('unknown_status_source', key)
            state = next((row.get(k) for k in ('terminal_status', 'result_status',
                         'investigation_status', 'round4_status') if row.get(k)), None)
            status_counts[str(state)] += 1
            for field in ('investigation_status', 'round4_status'):
                if row.get(field) in PENDING_STATES:
                    audit.error('investigation_marker_still_pending', key + ': ' + field)
            if state in PENDING_STATES or not state:
                audit.error('investigation_not_finished', key + ': ' + str(state))
            elif state not in TERMINAL_STATES:
                audit.error('unknown_terminal_state', key + ': ' + str(state))
            elif 'is_final' in row and row['is_final'] is not True:
                audit.error('status_explicitly_intermediate', key)
            else:
                terminal.append(key)
            attempts = row.get('round4_attempts', row.get('new_attempts', []))
            if not isinstance(attempts, list) or not attempts:
                audit.error('no_current_round_attempt', key)
            # Prior route history is deliberately not counted as a round-4 attempt.
            for attempt in attempts if isinstance(attempts, list) else []:
                if not isinstance(attempt, dict):
                    audit.error('invalid_attempt', key)
                elif not any(attempt.get(k) for k in ('outcome', 'result', 'evidence_path',
                                                     'evidence_paths', 'observed', 'evidence')):
                    audit.error('attempt_without_outcome_or_evidence', key)
                else:
                    check_local_evidence_paths(audit, attempt, 'attempt ' + key)
            check_local_evidence_paths(audit, row.get('evidence_paths', []), 'status ' + key)
    audit.sections['frozen_scope'] = {
        'expected': 65, 'chinese_expected': 24, 'international_and_other_expected': 41,
        'status_identities': len(statuses), 'terminal_investigations': len(set(terminal)),
        'identities_match': set(statuses) == set(frozen),
        'all_terminal': len(set(terminal)) == 65 and set(statuses) == set(frozen),
        'status_counts': dict(status_counts), 'baseline_sha256': BASELINE_SHA256,
    }
    return frozen, statuses


def file_refs(value):
    """Yield explicit hash-bearing file declarations, including HTML bundle forms."""
    for row in walk(value):
        for key in ('path', 'local_path', 'file', 'local_file', 'file_path', 'manifest_file'):
            if isinstance(row.get(key), str) and row.get('sha256'):
                yield row[key], row['sha256'], row.get('bytes')
                break
        if row.get('archived_file') and row.get('sha256'):
            yield row['archived_file'], row['sha256'], row.get('bytes')
        for key, hash_key, size_key in (
            ('original_html', 'sha256', 'bytes'),
            ('body_html', 'body_sha256', 'body_bytes'),
            ('offline_html', 'offline_sha256', 'offline_bytes'),
            ('manifest_path', 'manifest_sha256', 'manifest_bytes'),
            ('manifest_file', 'manifest_sha256', 'manifest_bytes'),
        ):
            if isinstance(row.get(key), str) and row.get(hash_key):
                yield row[key], row[hash_key], row.get(size_key)


def check_manifests(audit):
    count = 0
    paths = set()
    for base in (PRIVATE, ROOT / 'papers/human-expression/round4', BASE / 'fulltext-round4'):
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if path.suffix not in {'.json', '.jsonl'}:
                continue
            if not any(word in path.name for word in ('manifest', 'receipt', 'index')):
                continue
            value = audit.load(path)
            refs = list(file_refs(value))
            if refs:
                count += 1
            for value_path, digest, size in refs:
                p = audit.file(value_path, digest, size, audit.relative(path), require_hash=True)
                if p:
                    paths.add(audit.relative(p))
            for record in walk(value):
                page = record.get('printed_page')
                if type(page) is int:
                    for field in ('path', 'local_path', 'file'):
                        if isinstance(record.get(field), str):
                            p = audit.path(record[field], 'manifest printed page')
                            if p:
                                audit.file_pages[audit.relative(p)] = page
                            break
    audit.sections['private_manifests'] = {'manifests_with_hash_records': count,
                                          'unique_files_hash_checked': len(paths),
                                          'scope': 'private manifests and saved round4 file/access receipts; raw originals remain private'}
    return paths


def pick(row, *keys):
    return next((row[key] for key in keys if row.get(key) is not None), None)


def normalize_card(row):
    # The two authored schemas remain intact.  Validation adapts explicit aliases.
    return {
        'id': pick(row, 'id', 'card_id'),
        'source': identity(row),
        'title': pick(row, 'book', 'title'),
        'author': row.get('author'),
        'edition': pick(row, 'edition', 'consulted_edition'),
        'method': pick(row, 'read_method', 'method'),
        'claim': pick(row, 'claim', 'author_claim_paraphrase'),
        'conditions': pick(row, 'conditions', 'applicability_conditions'),
        'inference': pick(row, 'editorial_inference', 'renhua_research_implications'),
        'limits': pick(row, 'limits', 'limits_and_cannot_infer'),
        'claim_status': pick(row, 'claim_status', 'implications_status'),
        'topic': pick(row, 'topic', 'section'),
        'pages': row.get('printed_pages'),
        'evidence': pick(row, 'private_evidence_files', 'evidence_files'),
    }


def check_classics(audit, sources, hashed_paths):
    paths = sorted((BASE / 'classics-round4').glob('*-cards.jsonl'))
    prefixes = {p.name.split('-', 1)[0] for p in paths}
    for prefix in CLASSIC_REQUIRED:
        if prefix not in prefixes:
            audit.error('missing_classic_cards', prefix)
    if any(':ZH079-' in key for key in sources) and 'ZH079' not in prefixes:
        audit.error('missing_classic_cards', 'ZH079 exists as a new source but has no cards')
    seen = set()
    book_counts = {}
    for path in paths:
        prefix = path.name.split('-', 1)[0]
        rows = audit.load(path)
        all_pages = set()
        source_ids = set()
        for row in rows:
            card = normalize_card(row)
            cid = card['id']
            if not cid or cid in seen:
                audit.error('duplicate_or_missing_card_id', str(cid))
            seen.add(cid)
            for field in ('source', 'title', 'author', 'edition', 'method', 'claim',
                          'conditions', 'inference', 'limits', 'claim_status', 'topic'):
                if not card[field]:
                    audit.error('missing_classic_common_field', str(cid) + ': ' + field)
            source_ids.add(card['source'])
            if card['source'] not in sources:
                audit.error('unknown_classic_source', str(cid) + ': ' + str(card['source']))
            elif sources[card['source']].get('read_status') != 'partial':
                audit.error('classic_selected_reading_not_partial', str(card['source']))
            pages = card['pages']
            if not isinstance(pages, list) or not pages or any(type(n) is not int or n < 1 for n in pages):
                audit.error('invalid_printed_pages', str(cid))
                pages = []
            # Chen's two endpoints explicitly describe a complete-section range.
            if row.get('section_read_extent') == 'complete_section' and len(pages) == 2:
                pages = list(range(min(pages), max(pages) + 1))
            elif len(set(pages)) != len(pages):
                audit.error('duplicate_printed_page', str(cid))
            if pages and max(pages) > PAGE_LIMITS.get(prefix, 100000):
                audit.error('printed_page_outside_consulted_edition', str(cid))
            all_pages.update(pages)
            files = card['evidence']
            if not isinstance(files, list) or not files:
                audit.error('missing_card_evidence', str(cid))
                continue
            evidenced_pages = set()
            for value in files:
                p = audit.file(value, context='classic ' + str(cid))
                if not p:
                    continue
                rel = audit.relative(p)
                if not rel.startswith('.harness/research-20261020/round4/'):
                    audit.error('classic_evidence_not_private_round4', rel)
                if rel not in hashed_paths:
                    audit.error('classic_evidence_missing_manifest_hash', str(cid) + ': ' + rel)
                match = re.search(r'(?:^|[/_-])p0*(\d+)', rel)
                if match:
                    evidenced_pages.add(int(match.group(1)))
                if rel in audit.file_pages:
                    evidenced_pages.add(audit.file_pages[rel])
            if pages and not set(pages).issubset(evidenced_pages):
                audit.error('card_page_without_named_image', str(cid) + ': '
                            + repr(sorted(set(pages) - evidenced_pages)))
            if row.get('self_constructed_counterexample', {}).get('is_from_book') is True:
                audit.error('self_example_misattributed_to_book', str(cid))
        report = path.with_name(path.name.replace('-cards.jsonl', '-reading.md'))
        if not report.is_file():
            audit.error('classic_report_missing', audit.relative(report))
        book_counts[prefix] = {'cards': len(rows), 'distinct_printed_pages_named_by_cards': len(all_pages),
                               'page_count_scope': 'Card-referenced pages only; complete reading scope is separately recorded in the reading report and ledger',
                               'source_records': sorted(x for x in source_ids if x)}
    audit.sections['classics'] = {'books': len(book_counts), 'cards': len(seen),
                                  'by_book': book_counts}


def value_retained(expected, actual):
    """Permit appended prose/list evidence, never silently coerce booleans or IDs."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and value_retained(v, actual[k])
                                                for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and all(any(value_retained(v, a) for a in actual)
                                               for v in expected)
    if isinstance(expected, str) and isinstance(actual, str):
        return re.sub(r'\s+', '', expected) in re.sub(r'\s+', '', actual)
    return type(expected) is type(actual) and expected == actual


def check_additional_reading_cards(audit, sources, hashed_paths):
    """Check the two distinct non-classic schemas without inventing book fields."""
    folder = BASE / 'fulltext-round4'
    seen = set()
    counts = collections.Counter()
    classic_ids = {pick(row, 'id', 'card_id')
                   for path in (BASE / 'classics-round4').glob('*-cards.jsonl')
                   for row in audit.load(path)}
    for path in sorted(folder.glob('*-cards.jsonl')):
        for row in audit.load(path):
            key = identity(row)
            card_id = pick(row, 'id', 'card_id') or key
            if not card_id or card_id in seen or card_id in classic_ids:
                audit.error('additional_reading_card_id', audit.relative(path) + ': ' + str(card_id))
            seen.add(card_id)
            if key not in sources:
                audit.error('additional_reading_card_source', str(card_id) + ': ' + str(key))
            if path.name == 'international-reading-cards.jsonl':
                fields = ('read_status', 'read_scope', 'method_or_argument', 'findings',
                          'limits', 'interpretation_type')
                if row.get('read_status') not in {'partial', 'full'}:
                    audit.error('international_reading_card_status', str(card_id))
                check_local_evidence_paths(audit, row.get('evidence_locator', []), str(card_id))
            else:
                fields = ('section', 'printed_pages',
                          'applicability_conditions', 'limits_and_cannot_infer',
                          'renhua_research_implications', 'implications_status', 'evidence_files')
                if not pick(row, 'author_claim_paraphrase', 'direct_observations'):
                    audit.error('additional_reading_card_no_claim_or_observation', str(card_id))
                pages = row.get('printed_pages', [])
                if not pages or any(type(page) is not int or page < 1 for page in pages):
                    audit.error('additional_reading_card_pages', str(card_id))
                for value in row.get('evidence_files', []):
                    p = audit.file(value, context='additional card ' + str(card_id))
                    if p and audit.relative(p) not in hashed_paths:
                        audit.error('additional_card_evidence_without_hash_manifest', str(card_id) + ': ' + value)
            for field in fields:
                if not row.get(field):
                    audit.error('additional_reading_card_missing_field', str(card_id) + ': ' + field)
            counts[path.name] += 1
    audit.sections['additional_reading_cards'] = {'card_records': len(seen),
                                                'by_file': dict(counts),
                                                'schemas_checked_separately': True}


def check_proposals(audit, sources, before):
    proposal_files = sorted((BASE / 'fulltext-round4').glob('*source-updates.jsonl'))
    proposal_files += sorted((BASE / 'fulltext-round4').glob('*source-proposal.json'))
    proposal_files += sorted((BASE / 'fulltext-round4').glob('*source-proposals.jsonl'))
    proposal_files += sorted((BASE / 'classics-round4').glob('*source-update.json'))
    proposal_files += sorted((BASE / 'classics-round4').glob('*source-proposal.json'))
    checked = 0
    proposed_fields = collections.defaultdict(set)
    for path in proposal_files:
        loaded = audit.load(path)
        rows = loaded if isinstance(loaded, list) else [loaded]
        for row in rows:
            key = identity(row)
            if not key and row.get('id'):
                matches = [k for k in sources if k.endswith(':' + row['id'])]
                key = matches[0] if len(matches) == 1 else None
            if key not in sources:
                audit.error('proposal_source_not_found', audit.relative(path) + ': ' + str(key))
                continue
            updates = row.get('updates')
            if updates is None:
                wrappers = {'record_id', 'before', 'evidence', 'source_record_id',
                            'parent_record_id', 'proposal_only',
                            'source_proposal_status', 'source_card_modified'}
                updates = {k: v for k, v in row.items() if k not in wrappers}
            if not isinstance(updates, dict) or not updates:
                audit.error('empty_or_invalid_proposal', str(key))
                continue
            checked += 1
            for field, expected in updates.items():
                proposed_fields[key].add(field)
                if field not in sources[key] or not value_retained(expected, sources[key][field]):
                    audit.error('proposal_field_not_retained', key + ': ' + field
                                + ' [' + audit.relative(path) + ']')
    for key, old in before.items():
        if key not in sources:
            audit.error('baseline_source_removed', key)
            continue
        for field in ('id', 'title', 'authors', 'year', 'isbn', 'doi'):
            if old.get(field) != sources[key].get(field) and field not in proposed_fields[key]:
                audit.error('unproposed_bibliographic_drift', key + ': ' + field)
    # The 1996 alternate edition must not make the 2014 target look read.
    alternates = [key for key in sources if ':ZH079-' in key]
    targets = [key for key in before if ':ZH007-' in key]
    for key in alternates:
        if sources[key].get('year') != 1996:
            audit.error('alternate_edition_year_drift', key)
        link_text = json.dumps(sources[key], ensure_ascii=False)
        links = audit.load(BASE / 'work-linkages.jsonl')
        related = [r for r in links if key in list(strings(r))]
        for target in targets:
            if target not in link_text and not any(target in list(strings(r)) for r in related):
                audit.error('alternate_edition_link_missing', key + ' -> ' + target)
            if sources.get(target, {}).get('read_status') != before[target].get('read_status'):
                audit.error('alternate_edition_overwrote_target_read_status', target)
    audit.sections['proposals'] = {'proposal_files': len(proposal_files),
                                    'proposals_checked': checked,
                                    'alternate_edition_sources': alternates,
                                    'matching_is_static_not_semantic_proof': True}


def receipt_sources(row):
    values = [identity(row), row.get('source_id')]
    values += row.get('source_ids', []) or []
    values += row.get('source_records', []) or []
    return {x for x in values if isinstance(x, str) and ':' in x}


def complete_book_receipt(row):
    extent = str(row.get('document_extent', row.get('format', ''))).lower()
    if any(s in extent for s in ('preview', 'sample', 'preface_only', 'frontmatter')):
        return False
    return row.get('complete_book') is True or row.get('complete_book_body_html') is True


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'img':
            self.sources.append(dict(attrs).get('src', ''))

    handle_startendtag = handle_starttag


def image_sources(path):
    parser = ImageSources()
    parser.feed(path.read_text(errors='replace'))
    return parser.sources


def check_bundle_images_and_source_bytes(audit, manifest, context):
    images = manifest.get('image_files', [])
    by_url = {}
    actual_bytes = 0
    for item in images:
        path = audit.file(item.get('archived_file'), item.get('sha256'), item.get('bytes'),
                          context + ' archived image', require_hash=True, require_size=True)
        url = item.get('url')
        if not url or url in by_url:
            audit.error('bundle_image_mapping_missing_or_duplicate', context)
        if path:
            by_url[url] = path
            actual_bytes += audit.file_cache[path][1]
    observed_urls = set()
    for item in manifest.get('files', []):
        original = audit.file(item.get('original_html'), item.get('sha256'), item.get('bytes'),
                              context + ' original source HTML', require_hash=True, require_size=True)
        if original:
            actual_bytes += audit.file_cache[original][1]
        body = audit.path(item['body_html'], context + ' body images') if item.get('body_html') else None
        offline = audit.path(item['offline_html'], context + ' offline images') if item.get('offline_html') else None
        if not body or not body.is_file():
            continue
        sources = image_sources(body)
        observed_urls.update(sources)
        if sources and (not offline or not offline.is_file()):
            audit.error('bundle_image_offline_body_missing', context + ': ' + item.get('label', ''))
            continue
        local_sources = image_sources(offline) if offline and offline.is_file() else []
        if len(sources) != len(local_sources):
            audit.error('bundle_body_offline_image_count', context + ': ' + item.get('label', ''))
        for src, local_src in zip(sources, local_sources):
            if src not in by_url:
                audit.error('bundle_body_image_not_archived', context + ': ' + item.get('label', ''))
                continue
            parsed = urlsplit(local_src)
            if parsed.scheme or parsed.netloc or not parsed.path:
                audit.error('bundle_offline_image_not_local', context + ': ' + item.get('label', ''))
                continue
            local_path = (offline.parent / unquote(parsed.path)).resolve()
            if local_path != by_url[src] or not local_path.is_file():
                audit.error('bundle_offline_image_mapping', context + ': ' + item.get('label', ''))
    if observed_urls != set(by_url):
        audit.error('bundle_image_inventory_not_body_closed', context)
    return actual_bytes


def check_receipts_and_queue(audit, sources, before, frozen, statuses):
    paths = sorted((BASE / 'fulltext-round4').glob('*receipts.jsonl'))
    # Supplemental acquisitions (for example a newly identified errata paper)
    # are outside the frozen 65 identities.  Select their actual new file paths
    # rather than treating every historical CNKI receipt as a round-4 result.
    old_pdf_values = {s for row in before.values() for s in strings(row)
                      if s.endswith('.pdf') and (s.startswith('papers/') or s.startswith(str(ROOT) + '/'))}
    old_pdf_paths = set()
    for value in old_pdf_values:
        p = audit.path(value, 'baseline PDF')
        if p:
            old_pdf_paths.add(audit.relative(p))
    # The round-4 source-card snapshot intentionally omitted unchanged practice
    # and citation branches.  The preceding independent audit actually hashed
    # all 82 PDFs; use those saved path+hash observations, not current filenames
    # or a blanket branch exclusion, to identify unchanged historical files.
    historical_audit = ROOT / '.harness/research-20261020/final-zh-review/observed.json'
    audit.file(str(historical_audit), HISTORICAL_PDF_AUDIT_SHA256,
               context='previous independent 82-PDF observation snapshot', require_hash=True)
    historical_pdfs = audit.load(historical_audit).get('pdf_actual_checks', [])
    expected_old_count = audit.load(FROZEN / 'validation.json').get('pdf_files')
    if (len(historical_pdfs) != expected_old_count
            or len({row.get('path') for row in historical_pdfs}) != expected_old_count
            or len({row.get('sha256') for row in historical_pdfs}) != expected_old_count
            or not all(row.get('verified') is True for row in historical_pdfs)):
        audit.error('historical_pdf_audit_scope', 'previous verified PDF list must match frozen PDF count')
    for row in historical_pdfs:
        p = audit.file(row.get('path'), row.get('sha256'), row.get('bytes'),
                       'historical pre-round4 PDF audit', require_hash=True, require_size=True)
        if p:
            old_pdf_paths.add(audit.relative(p))
    pdfs = audit.load(BASE / 'acquisition/pdf-files.jsonl')
    new_pdfs = [row for row in pdfs if row.get('path') not in old_pdf_paths]
    new_pdf_paths = {row.get('path') for row in new_pdfs}
    rows = []
    receipt_paths = set()
    complete_books = set()
    complete_articles = set()
    bundle_count = 0
    input_rows = []
    expanded_bundle_snapshots = []
    seen_bundles = {}
    child_receipts = set()
    access_count = 0
    for path in paths:
        for row in audit.load(path):
            if (row.get('format') == 'html_bundle' and isinstance(row.get('files'), list)
                    and row.get('expected_chapters') and not pick(row, 'manifest_path', 'manifest_file', 'file')):
                expanded_bundle_snapshots.append((path, row))
                continue
            input_rows.append((path, row))
            # Access receipts honestly describe failures/online-only access.
            # A referenced detailed file receipt, rather than the access result,
            # supplies the byte/hash/completeness declarations for acquisitions.
            for value in strings(row):
                if value.startswith('papers/') and value.endswith('/receipt.json'):
                    p = audit.path(value, 'access receipt detailed file evidence')
                    if p and p not in child_receipts:
                        child_receipts.add(p)
                        input_rows.append((p, audit.load(p)))
    supplemental_count = 0
    global_receipts = BASE / 'acquisition/cnki-receipts.jsonl'
    for row in audit.load(global_receipts, required=False):
        if not any(value in new_pdf_paths for value, _, _ in file_refs(row)):
            continue
        supplemental_count += 1
        normalized = dict(row)
        if not receipt_sources(normalized):
            matches = [key for key in sources if key.rsplit(':', 1)[-1] == row.get('id')]
            if len(matches) == 1:
                normalized['source_records'] = matches
                normalized['validation_association_resolved_from_receipt_id'] = True
        input_rows.append((global_receipts, normalized))
    # An expanded manifest snapshot is evidence about the same package, not a
    # second acquisition.  It must equal the hash-anchored manifest saved by an
    # ordinary receipt; do not infer its path from the source's name.
    for path, snapshot in expanded_bundle_snapshots:
        anchors = [(p, row) for p, row in input_rows
                   if row.get('format') == 'html_bundle'
                   and row.get('id') == snapshot.get('id')
                   and receipt_sources(row) == receipt_sources(snapshot)]
        if not anchors:
            audit.error('expanded_bundle_without_anchor_receipt', audit.relative(path) + ': ' + str(snapshot.get('id')))
            continue
        for _, anchor in anchors:
            value = pick(anchor, 'manifest_path', 'manifest_file', 'file', 'path', 'local_path')
            p = audit.path(value, 'expanded bundle anchor') if value else None
            if not p or audit.load(p) != snapshot:
                audit.error('expanded_bundle_snapshot_drift', audit.relative(path) + ': ' + str(snapshot.get('id')))
    for path, row in input_rows:
            rows.append(row)
            associations = receipt_sources(row)
            if not associations or not associations.issubset(sources):
                audit.error('receipt_source_identity', audit.relative(path) + ': ' + repr(sorted(associations)))
            refs = list(file_refs(row))
            if not refs:
                attempts = row.get('attempts')
                if isinstance(attempts, list) and attempts:
                    access_count += 1
                    check_local_evidence_paths(audit, attempts, 'access receipt ' + str(identity(row)))
                else:
                    audit.error('file_receipt_without_hashed_file', audit.relative(path) + ': ' + str(row.get('id')))
            for value, digest, size in refs:
                p = audit.file(value, digest, size, audit.relative(path), require_hash=True,
                               require_size=True)
                if p:
                    receipt_paths.add(audit.relative(p))
            if row.get('format') == 'html_bundle':
                manifest_path = pick(row, 'manifest_path', 'manifest_file', 'file', 'path', 'local_path')
                if not manifest_path:
                    manifest_path = next((v for v, _, _ in refs if v.endswith('/manifest.json')), None)
                p = audit.path(manifest_path, 'HTML bundle manifest') if manifest_path else None
                manifest = audit.load(p) if p else {}
                bundle_key = (row.get('id'), tuple(sorted(associations)))
                digest = audit.file_cache.get(p, (None, None))[0] if p else None
                if bundle_key in seen_bundles:
                    if seen_bundles[bundle_key] != digest:
                        audit.error('conflicting_duplicate_bundle_receipt', str(row.get('id')))
                    continue
                seen_bundles[bundle_key] = digest
                bundle_count += 1
                if manifest.get('complete_book_body_html') is not True:
                    audit.error('bundle_not_complete_book_body', str(row.get('id')))
                if manifest.get('expected_chapters') != manifest.get('verified_chapters') or not manifest.get('expected_chapters'):
                    audit.error('bundle_chapter_coverage', str(row.get('id')))
                expected_chapters = manifest.get('expected_chapters')
                if type(expected_chapters) is not int or expected_chapters < 1:
                    audit.error('bundle_invalid_expected_chapters', str(row.get('id')))
                    expected_chapters = 0
                validation = manifest.get('completeness_validation', {})
                if validation.get('missing_substantive_components_detected') != []:
                    audit.error('bundle_missing_substantive_components', str(row.get('id')))
                for field in ('chapter_count_matches_official_WAC_TOC', 'introduction_nonempty',
                              'references_nonempty', 'copyright_license_page_present',
                              'all_observed_mirror_body_images_archived'):
                    if validation.get(field) is not True:
                        audit.error('bundle_completeness_evidence_missing', str(row.get('id')) + ': ' + field)
                # The complete WAC page, a short Parlor search-cache, and a
                # mirror's original-book Contents leaf are distinct evidence.
                # Volume 2 has no separate Contents leaf: do not demand a false
                # declaration merely to satisfy the check.
                toc_checked = False
                for toc in manifest.get('toc_evidence', []):
                    if toc.get('complete_chapter_count') != manifest.get('expected_chapters'):
                        continue
                    toc_path = audit.file(toc.get('file'), toc.get('sha256'), toc.get('bytes'),
                                          'complete WAC TOC evidence', require_hash=True,
                                          require_size=True)
                    if toc_path:
                        numbers = {int(n) for n in re.findall(r'/chapter(\d+)\.pdf',
                                                            toc_path.read_text(errors='replace'))}
                        if numbers != set(range(1, expected_chapters+1)):
                            audit.error('bundle_toc_actual_chapter_links', str(row.get('id')))
                        else:
                            toc_checked = True
                if not toc_checked:
                    audit.error('bundle_complete_toc_not_archived', str(row.get('id')))
                for value, digest, size in file_refs(manifest):
                    audit.file(value, digest, size, 'HTML bundle contents', require_hash=True)
                originals = manifest.get('files', [])
                labels = [item.get('label', '') for item in originals]
                chapters = [s for s in labels if re.fullmatch(r'chapter-\d+', s)]
                if len(chapters) != manifest.get('expected_chapters') or len(chapters) != len(set(chapters)):
                    audit.error('bundle_actual_chapter_labels', str(row.get('id')))
                if {int(s.split('-')[1]) for s in chapters} != set(range(1, expected_chapters+1)):
                    audit.error('bundle_actual_chapter_number_set', str(row.get('id')))
                for label in ('introduction', 'references', 'copyright'):
                    if label not in labels:
                        audit.error('bundle_required_part_missing', str(row.get('id')) + ': ' + label)
                for item in originals:
                    # Unit JSONL has no printed-page or completeness authority.
                    if item.get('text_units'):
                        audit.file(item['text_units'], context='HTML locator units')
                    if item.get('label') in chapters + ['introduction', 'references', 'copyright']:
                        body_path = item.get('body_html')
                        body = audit.file(body_path, item.get('body_sha256'), context='substantive HTML body', require_hash=True) if body_path else None
                        if body is None:
                            audit.error('bundle_body_missing', str(row.get('id')) + ': ' + item.get('label', ''))
                        elif not re.sub(r'<[^>]+>|\s+', '', body.read_text(errors='replace')):
                            audit.error('bundle_body_empty', audit.relative(body))
                scope = str(manifest.get('bytes_scope', ''))
                actual_source_bytes = check_bundle_images_and_source_bytes(audit, manifest, str(row.get('id')))
                if scope == 'original_html_plus_archived_book_images_only' or scope.startswith('original_html_plus_archived_book_images_only;'):
                    if manifest.get('bytes') != actual_source_bytes:
                        audit.error('bundle_source_bytes_mismatch', str(row.get('id')))
                    if row.get('bundle_total_bytes') != manifest.get('bytes'):
                        audit.error('bundle_receipt_aggregate_mismatch', str(row.get('id')))
                else:
                    audit.error('bundle_bytes_scope_not_declared', str(row.get('id')))
                if complete_book_receipt(manifest):
                    complete_books.update(associations)
            elif complete_book_receipt(row):
                complete_books.update(associations)
            if row.get('complete_article') is True or row.get('format') in {
                'complete_article_body_text_transcription', 'author_public_html_transcription'}:
                complete_articles.update(associations)
            extent = str(row.get('document_extent', '')).lower()
            if any(s in extent for s in ('sample', 'preview', 'preface_only', 'frontmatter')):
                if row.get('complete_book') is True:
                    audit.error('sample_claimed_as_complete_book', str(row.get('id')))
    # Independently enumerate new registered PDFs, not only successful receipt rows.
    for row in new_pdfs:
        p = audit.file(row.get('path'), row.get('sha256'), row.get('bytes'),
                       'new PDF registry entry', require_hash=True, require_size=True)
        if p and not p.read_bytes().startswith(b'%PDF-'):
            audit.error('new_pdf_magic_invalid', audit.relative(p))
        if row.get('path') not in receipt_paths:
            audit.error('new_pdf_missing_round4_receipt', str(row.get('path')))
        if not row.get('source_records') or not set(row['source_records']).issubset(sources):
            audit.error('new_pdf_source_association', str(row.get('path')))
    registered = {row.get('path') for row in pdfs}
    for p in (ROOT / 'papers/human-expression/round4').rglob('*.pdf'):
        if audit.relative(p) not in registered:
            audit.error('round4_pdf_unregistered', audit.relative(p))
    pending = unique_rows(audit, audit.load(BASE / 'acquisition/pending-access.jsonl'), 'current acquisition queue')
    cleared = set(frozen) - set(pending)
    for key in cleared:
        if frozen[key].get('type') in BOOK_TYPES:
            if key not in complete_books:
                audit.error('book_queue_cleared_without_complete_body', key)
        elif key not in complete_articles:
            audit.error('article_queue_cleared_without_complete_receipt', key)
    for key, row in sources.items():
        if row.get('full_book_obtained') is True and before.get(key, {}).get('full_book_obtained') is not True:
            if key not in complete_books:
                audit.error('new_complete_book_flag_without_full_receipt', key)
            elif key in pending:
                audit.error('complete_book_body_still_in_missing_queue', key)
    for key, row in statuses.items():
        if row.get('fulltext_gap_closed') is True and key in pending:
            # A native-PDF format gap belongs in a separate field/queue, not in
            # a queue whose reason says the complete body has not been obtained.
            audit.error('closed_body_gap_still_in_fulltext_queue', key)
    audit.sections['acquisition'] = {
        'receipt_files': len(paths), 'receipt_records': len(rows),
        'access_receipt_records': access_count, 'referenced_detailed_receipts': len(child_receipts),
        'new_pdf_receipts_selected_from_global_cnki_log': supplemental_count,
        'expanded_bundle_snapshot_records': len(expanded_bundle_snapshots),
        'new_registered_pdfs': len(new_pdfs),
        'historical_pdf_paths_checked': len(historical_pdfs),
        'historical_pdf_baseline': audit.relative(historical_audit),
        'historical_pdf_baseline_sha256': HISTORICAL_PDF_AUDIT_SHA256,
        'html_book_bundles': bundle_count, 'complete_book_body_records': sorted(complete_books),
        'complete_article_records': sorted(complete_articles),
        'frozen_ids_cleared_from_file_queue': sorted(cleared),
        'frozen_ids_remaining_in_file_queue': sorted(set(frozen) & set(pending)),
        'note': 'Investigation completion, body-text availability, original PDF, and full reading are separate states; retaining a file gap after complete HTML is not itself an error.',
    }
    return rows


def check_protected_runtime(audit):
    try:
        changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--',
                                          *PROTECTED_PATHS], cwd=ROOT, text=True).splitlines()
        untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard',
                                            '--', *PROTECTED_PATHS], cwd=ROOT, text=True).splitlines()
        if changed or untracked:
            audit.error('runtime_or_skill_diff', repr(changed + untracked))
        audit.sections['runtime'] = {'protected_paths': list(PROTECTED_PATHS),
                                     'changed_tracked': changed, 'untracked': untracked,
                                     'no_diff_against_HEAD': not (changed or untracked)}
    except (OSError, subprocess.CalledProcessError) as exc:
        audit.error('git_runtime_check_failed', str(exc))


def check_manual_readback(audit):
    path = PRIVATE / 'independent-review/readback.json'
    record = audit.load(path)
    for item in record.get('target_file_sha256', []):
        audit.file(item.get('path'), item.get('sha256'), context='independent manual readback target', require_hash=True)
    findings = record.get('findings', [])
    if not findings or not record.get('target_file_sha256'):
        audit.error('independent_manual_readback_missing', audit.relative(path))
    audit.sections['manual_readback'] = {
        'method': record.get('method'), 'findings': findings,
        'targets_hash_checked': len(record.get('target_file_sha256', [])),
        'limits': record.get('limits'),
    }


def check_public_content(audit, receipts):
    public_files = sorted(BASE.rglob('*'))
    binary = []
    for path in public_files:
        if path.is_file() and path.suffix.lower() in RESTRICTED_SUFFIXES:
            binary.append(audit.relative(path))
    if binary:
        audit.error('research_original_or_scan_in_public_docs', repr(binary))
    round4_files = [p for folder in (BASE / 'fulltext-round4', BASE / 'classics-round4')
                    if folder.exists() for p in folder.rglob('*') if p.suffix in {'.md', '.json', '.jsonl'}]
    public_texts = {}
    for path in round4_files:
        text = path.read_text()
        public_texts[path] = re.sub(r'\s+', '', text)
        for match in re.finditer(r'https?://[^\s<>"\)]+', text):
            try:
                keys = {k.lower() for k, _ in parse_qsl(urlsplit(match.group()).query)}
            except ValueError:
                continue
            if keys & SENSITIVE_QUERY_KEYS:
                # Never print the value or full signed URL in the public review.
                audit.error('session_or_signed_query_in_public_docs',
                            audit.relative(path) + ': query keys ' + repr(sorted(keys & SENSITIVE_QUERY_KEYS)))
    # Exact long-text copying screen; paraphrase/legal judgement still needs review.
    text_paths = set(PRIVATE.rglob('*.txt'))
    for row in receipts:
        for s in strings(row):
            if s.endswith(('.txt', '.html')) and not s.startswith(('http:', 'https:')):
                p = audit.path(s, 'raw text copy screen')
                if p and p.is_file():
                    text_paths.add(p)
    hits = []
    for raw in sorted(text_paths):
        if raw.stat().st_size > 20_000_000:
            audit.warn('large_text_copy_screen_skipped', audit.relative(raw))
            continue
        text = re.sub(r'\s+', '', raw.read_text(errors='replace'))
        for offset in range(0, max(0, len(text)-499), 250):
            segment = text[offset:offset+500]
            for path, public in public_texts.items():
                if segment in public:
                    hits.append({'public_path': audit.relative(path), 'private_path': audit.relative(raw)})
                    break
            if hits and hits[-1]['private_path'] == audit.relative(raw):
                break
    if hits:
        audit.error('long_exact_raw_text_in_public_round4_docs', repr(hits))
    audit.sections['public_content'] = {
        'public_binary_originals_or_scans': binary, 'round4_text_files_screened': len(public_texts),
        'private_text_files_screened': len(text_paths), 'long_exact_text_copy_hits': hits,
        'limits': 'Static screen for binaries, signed-query keys and exact 500-character runs; does not prove copyright compliance or judge every quotation/paraphrase.',
    }


def report_markdown(result):
    sec = result['checks']
    scope = sec['frozen_scope']
    classic = sec['classics']
    acquire = sec['acquisition']
    lines = ['# 第四轮独立静态验收', '',
             '结果：' + ('通过' if result['passed'] else '未通过') + '。校验身份、终态、字段保留、文件与散列；不证明调研穷尽、原文真实性或编辑效果。', '',
             '| 范围 | 检查结果 |', '|---|---|',
             '| 冻结身份 | 65项：中文24，其余41；基线散列锁定 |',
             f'| 调查终态 | {scope["terminal_investigations"]}/65；身份相符={scope["identities_match"]} |',
             f'| 经典阅读 | {classic["books"]}本，{classic["cards"]}卡；按所读页及证据核对，非全书通读 |',
             f'| 新PDF | {acquire["new_registered_pdfs"]}份；逐项回执、来源、大小、散列、magic |',
             f'| 完整正文HTML | {acquire["html_book_bundles"]}包；另核目录/章节/前后附属材料及图像，不当原版PDF |',
             f'| 冻结文件缺口 | 仍在队列{len(acquire["frozen_ids_remaining_in_file_queue"])}项；调查终态不等于全部取得 |',
             '| 运行时 | skills/commands/plugin/scripts/evals相对HEAD无改动，或错误列表明确列出 |', '',
             '受限材料的公开目录检查只覆盖二进制原件/扫描图、会话查询键与长段精确复制。推论归属和版权边界仍需结合人工阅读记录。', '',
             '## 错误', '']
    lines += ['- `' + e['code'] + '`：' + e['detail'] for e in result['errors']] or ['无。']
    lines += ['', '## 独立原页抽审与已修问题', '']
    for finding in sec['manual_readback']['findings']:
        lines += ['- `' + finding['id'] + '`（' + finding['status'] + '）：'
                  + finding['issue'] + ' ' + finding['resolution']]
    lines += ['', '## 保留事项', '']
    lines += ['- `' + e['code'] + '`：' + e['detail'] for e in result['warnings']] or ['无额外静态告警。']
    lines += ['', '本验收不编辑来源卡、生成目录、获取队列或运行时skill；结构化明细见[JSON](review-final-round4.json)。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final', action='store_true',
                        help='after owner confirms integration, write final review MD/JSON')
    args = parser.parse_args()
    audit = Audit()
    sources = source_map(audit, BASE)
    before = source_map(audit, FROZEN)
    frozen, statuses = check_frozen_and_status(audit, sources)
    hashed_paths = check_manifests(audit)
    check_classics(audit, sources, hashed_paths)
    check_additional_reading_cards(audit, sources, hashed_paths)
    check_proposals(audit, sources, before)
    receipts = check_receipts_and_queue(audit, sources, before, frozen, statuses)
    check_protected_runtime(audit)
    check_manual_readback(audit)
    check_public_content(audit, receipts)
    result = {
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phase': 'final_after_integration' if args.final else 'read_only_preflight',
        'passed': not audit.errors, 'checks': audit.sections,
        'unique_files_hash_checked': len(audit.hashed_files),
        'errors': audit.errors, 'warnings': audit.warnings,
        'scope': 'Round4 frozen65/status65, selected classics, proposals, file receipts and restrictions; not global source truth or editing effectiveness',
    }
    if args.final:
        (BASE / 'review-final-round4.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        (BASE / 'review-final-round4.md').write_text(report_markdown(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
