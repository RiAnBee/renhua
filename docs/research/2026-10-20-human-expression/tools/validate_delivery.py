#!/usr/bin/env python3
"""Check the saved research package, not the truth/effectiveness of its sources."""
import collections
import datetime
import hashlib
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-20-human-expression'


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def file_records(row):
    """Source cards use both legacy path strings and structured file records."""
    for item in row.get('files', []):
        if isinstance(item, str):
            yield {'path': item}
        elif isinstance(item, dict):
            yield item


def main():
    errors, warnings = [], []
    source_files = sorted(BASE.glob('*/sources.jsonl'))
    sources = []
    for path in source_files:
        seen = set()
        for row in jsonl(path):
            key = path.parent.name + ':' + row['id']
            if key in seen:
                errors.append('duplicate source ID ' + key)
            seen.add(key)
            if row.get('read_status') not in {'metadata', 'abstract', 'partial', 'full'}:
                errors.append('invalid reading status ' + key)
            for field in ('title', 'read_status'):
                if not row.get(field):
                    errors.append('missing ' + field + ': ' + key)
            if not row.get('authors') and not row.get('organization'):
                errors.append('missing author and source organization: ' + key)
            locator = row.get('canonical_url') or row.get('metadata_url')
            if not isinstance(locator, str) or not locator.startswith(('https://', 'http://')):
                errors.append('missing source URL ' + key)
            sources.append((key, row))
    catalog = jsonl(BASE / 'catalog.jsonl')
    if {key for key, _ in sources} != {row['record_id'] for row in catalog}:
        errors.append('catalog identities do not match source cards')
    for row in catalog:
        path = ROOT / row['source_record_file']
        actual = json.loads(path.read_text().splitlines()[row['source_record_line'] - 1])
        if actual['id'] != row['source_id'] or actual['read_status'] != row['read_status']:
            errors.append('catalog line/status drift: ' + row['record_id'])
    summary = json.loads((BASE / 'catalog-summary.json').read_text())
    if len(catalog) != summary['records']:
        errors.append('catalog total mismatch')
    for link in jsonl(BASE / 'work-linkages.jsonl'):
        for key in link['records']:
            if key not in {key for key, _ in sources}:
                errors.append('invalid work linkage ' + key)

    pdfs = jsonl(BASE / 'acquisition/pdf-files.jsonl')
    for row in pdfs:
        path = ROOT / row['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            errors.append('missing or changed PDF: ' + row['path'])
        if not row['source_records']:
            errors.append('unlinked PDF: ' + row['path'])
    pdf_summary = json.loads((BASE / 'acquisition/pdf-summary.json').read_text())
    if len(pdfs) != pdf_summary['pdf_files'] or sum(r['pages'] for r in pdfs) != pdf_summary['pages']:
        errors.append('PDF totals mismatch')
    if pdf_summary.get('errors') or pdf_summary.get('unlinked_files'):
        errors.append('PDF audit has unresolved errors or missing associations')
    cnki = jsonl(BASE / 'acquisition/cnki-receipts.jsonl')
    if len(cnki) != len({r['id'] for r in cnki}) or len(cnki) != len({r['sha256'] for r in cnki}):
        errors.append('CNKI receipt identity/hash duplication')

    # Complete body transcriptions/EPUB remain distinct from native PDFs.
    nonpdf_path = BASE / 'acquisition/round3-nonpdf-files.jsonl'
    nonpdf = jsonl(nonpdf_path) if nonpdf_path.is_file() else []
    for row in nonpdf:
        if row['record_id'] not in {key for key, _ in sources}:
            errors.append('unknown non-PDF source: ' + row['record_id'])
        for record in row['files']:
            path = ROOT / record['path']
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                errors.append('missing or changed non-PDF fulltext: ' + record['path'])

    # Check explicit Markdown file links. Raw paths inside prose are not inferred.
    checked_links = 0
    for path in BASE.rglob('*.md'):
        for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)\n]+)\)', path.read_text()):
            target = match.group(1).strip().strip('<>')
            if target.startswith(('https://', 'http://', 'mailto:', 'codex:', '#')):
                continue
            target = unquote(target.split('#', 1)[0])
            target = re.sub(r':\d+$', '', target)
            if not target:
                continue
            candidate = Path(target) if target.startswith('/') else path.parent / target
            checked_links += 1
            if not candidate.exists():
                errors.append(str(path.relative_to(BASE)) + ': broken file link ' + target)

    gh = json.loads((BASE / 'github/validation.json').read_text())
    if not gh.get('passed'):
        errors.append('GitHub structural validation not passed')
    if not gh.get('direct_queue_content_disposition_complete'):
        errors.append('GitHub finite core queue still lacks dispositions')
    # The original core can remain green while the later frozen queue is pending.
    # Require the current phase's explicit identities instead of reusing that flag.
    round3_required = (BASE / 'github/round3/README.md').is_file()
    if round3_required:
        for scope, expected in (('frozen_queue', 1810), ('scope_candidates', 12)):
            if gh.get('round3_' + scope + '_expected') != expected:
                errors.append('GitHub round3 expected scope missing or mismatched: ' + scope)
            if gh.get('round3_' + scope + '_reviewed') != expected:
                errors.append('GitHub round3 review count incomplete: ' + scope)
            if gh.get('round3_' + scope + '_disposition_complete') is not True:
                errors.append('GitHub round3 dispositions incomplete: ' + scope)
        if gh.get('candidate_not_yet_reviewed_remaining') != 0:
            errors.append('GitHub round3 still has candidates without review')
        if gh.get('round3_identity_errors') != []:
            errors.append('GitHub round3 identity validation missing or failed')
    counts = collections.Counter(row['read_status'] for _, row in sources)
    # Verified book files can live in any source branch. Samples are excluded.
    complete_book_ids = {key for key, row in sources if row.get('full_book_obtained') is True
                         and row.get('full_book_format') != 'html_bundle'
                         and any(key in pdf['source_records'] for pdf in pdfs)}
    complete_html_book_ids = set()
    for key, row in sources:
        if (row.get('full_book_obtained') is True
                and row.get('full_book_format') == 'html_bundle'
                and row.get('complete_book_body_html') is True):
            manifest = row.get('fulltext_bundle_manifest')
            if (not isinstance(manifest, str)
                    or not manifest.startswith('papers/human-expression/')
                    or not (ROOT / manifest).is_file()):
                errors.append('missing complete HTML book manifest: ' + key)
            else:
                complete_html_book_ids.add(key)
    epub_files = []
    for path in sorted((ROOT / 'papers/human-expression').rglob('*.epub')):
        rel = str(path.relative_to(ROOT))
        associations = [(key, f) for key, row in sources for f in file_records(row)
                        if f.get('path') == rel]
        if not associations:
            errors.append('unlinked EPUB: ' + rel)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for key, record in associations:
            if record.get('sha256') != digest:
                errors.append('EPUB hash drift: ' + key)
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.read('mimetype').decode().strip() != 'application/epub+zip':
                    errors.append('invalid EPUB mimetype: ' + rel)
                if not any(name.endswith('.opf') for name in archive.namelist()):
                    errors.append('EPUB missing package metadata: ' + rel)
        except Exception as exc:
            errors.append('invalid EPUB: ' + rel + ': ' + str(exc))
        epub_files.append(dict(path=rel, sha256=digest, bytes=path.stat().st_size,
                               source_records=[key for key, _ in associations]))
    warnings.extend(summary.get('warnings', []))
    warnings.append('full includes short guides; PDF acquisition and partial reading do not prove editing effects')
    result = dict(checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  source_records=len(sources), branches=len(source_files), reading_status=dict(counts),
                  pdf_files=len(pdfs), unique_pdf_hashes=len({r['sha256'] for r in pdfs}),
                  physical_pdf_pages=sum(r['pages'] for r in pdfs),
                  bytes=sum(r['bytes'] for r in pdfs), complete_open_book_files=len(complete_book_ids),
                  complete_book_record_ids=sorted(complete_book_ids),
                  complete_html_book_bundles=len(complete_html_book_ids),
                  complete_html_book_record_ids=sorted(complete_html_book_ids),
                  epub_files=len(epub_files), epub_details=epub_files,
                  cnki_receipts=len(cnki), markdown_file_links_checked=checked_links,
                  round3_nonpdf_fulltext_records=len(nonpdf),
                  round3_nonpdf_formats=dict(collections.Counter(row['format'] for row in nonpdf)),
                  github_indexed=gh.get('indexed_repositories'), github_queries=gh.get('queries'),
                  github_unique_search_identities=gh.get('unique_search_identities'),
                  github_core_dispositions_complete=gh.get('direct_queue_content_disposition_complete'),
                  github_round3_required=round3_required,
                  github_round3_scope={key: gh.get(key) for key in (
                      'round3_frozen_queue_expected', 'round3_frozen_queue_reviewed',
                      'round3_scope_candidates_expected', 'round3_scope_candidates_reviewed',
                      'round3_frozen_queue_disposition_complete',
                      'round3_scope_candidates_disposition_complete',
                      'candidate_not_yet_reviewed_remaining', 'round3_identity_errors')},
                  errors=errors, warnings=warnings, passed=not errors,
                  scope='Saved identities, counts, hashes, source locators, file links and finite core dispositions; not exhaustiveness, source truth or project effectiveness')
    (BASE / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
