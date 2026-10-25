#!/usr/bin/env python3
"""Apply reviewed research data proposals against the frozen round6 sources.

Default is read-only. --apply writes only the seven existing source registries;
catalog/queues/audits are rebuilt separately. The frozen originals are untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-20-human-expression'
ROUND = BASE / 'fulltext-round6'
FROZEN = ROOT / '.harness/research-20261020/round6/baseline'
FROZEN_MANIFEST_SHA256 = '514bd84cc79674467ff84cb348afd8407cc8d8014a58fd466a3b3adcebd56209'


def readl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def keyed(rows, label):
    result = {row['id']: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate source IDs: ' + label)
    return result


def verify_frozen_baseline():
    manifest_path = FROZEN / 'frozen-manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != FROZEN_MANIFEST_SHA256:
        raise ValueError('Frozen round6 manifest changed; do not merge against a new denominator')
    seen = set()
    for record in json.loads(manifest_path.read_text()):
        name = record.get('path')
        path = (FROZEN / name).resolve() if isinstance(name, str) else None
        if not path or name in seen or not path.is_relative_to(FROZEN.resolve()):
            raise ValueError('Invalid/duplicate frozen manifest path: ' + str(name))
        seen.add(name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != record.get('sha256'):
            raise ValueError('Frozen baseline file changed: ' + name)
    return len(seen)


def verify_proposal_before(proposal, original):
    before = proposal.get('before', {})
    if not isinstance(before, dict):
        raise ValueError('Proposal before must be a field mapping: ' + proposal['record_id'])
    for field, expected in before.items():
        if original.get(field) != expected:
            raise ValueError('Proposal before differs from frozen baseline: '
                             + proposal['record_id'] + ': ' + field)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    frozen_files_checked = verify_frozen_baseline()
    baseline = {p.parent.name: readl(p) for p in sorted(FROZEN.glob('*/sources.jsonl'))}
    if len(baseline) != 7:
        raise ValueError('Expected the seven frozen source registries')
    frozen_sources = {branch: keyed(rows, branch + ' baseline') for branch, rows in baseline.items()}
    patches, inputs = {}, []
    for path in sorted(ROUND.glob('*-source-updates.jsonl')):
        payload = path.read_bytes()
        inputs.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(payload).hexdigest()))
        for proposal in readl(path):
            identity = proposal['record_id']
            branch, source_id = identity.split(':', 1)
            if branch not in baseline or identity in patches:
                raise ValueError('Unknown branch or competing proposal: ' + identity)
            verify_proposal_before(proposal, frozen_sources[branch].get(source_id, {}))
            update = proposal['updates']
            if 'id' in update and update['id'] != source_id:
                raise ValueError('Proposal/source ID mismatch: ' + identity)
            patches[identity] = update
    outputs, changed, added = {}, [], []
    for branch, original_rows in baseline.items():
        path = BASE / branch / 'sources.jsonl'
        old = keyed(original_rows, branch + ' baseline')
        current = keyed(readl(path), branch + ' current')
        candidate = dict(old)
        for identity, update in patches.items():
            patch_branch, source_id = identity.split(':', 1)
            if patch_branch == branch:
                candidate[source_id] = {**old.get(source_id, {}), **update}
                if candidate[source_id].get('id') != source_id:
                    raise ValueError('New proposal requires a source ID: ' + identity)
                if source_id not in old:
                    added.append(identity)
                elif candidate[source_id] != old[source_id]:
                    changed.append(identity)
        # Reruns accept already-applied identical data, but never overwrite an
        # unrelated edit or silently remove a source inserted outside this plan.
        for source_id, row in current.items():
            if row != old.get(source_id) and row != candidate.get(source_id):
                raise ValueError('Unreviewed source drift: ' + branch + ':' + source_id)
        if not set(old) <= set(current) or not set(current) <= set(candidate):
            raise ValueError('Unreviewed source removal/addition: ' + branch)
        order = list(old) + sorted(set(candidate) - set(old))
        outputs[path] = ''.join(json.dumps(candidate[key], ensure_ascii=False) + '\n' for key in order)
    # All input/source checks finish before any mutation.
    for entry in inputs:
        if hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Proposal changed during merge planning')
    if args.apply:
        for path, payload in outputs.items():
            temporary = path.with_suffix('.jsonl.round6-tmp')
            temporary.write_text(payload)
            temporary.replace(path)
    print(json.dumps(dict(applied=args.apply, frozen_manifest_sha256=FROZEN_MANIFEST_SHA256,
        frozen_files_checked=frozen_files_checked, proposal_files=inputs,
        proposals=len(patches), changed_existing=sorted(changed), new_records=sorted(added),
        source_rows=sum(len(readl(p)) for p in outputs) if args.apply else
                    sum(len(payload.splitlines()) for payload in outputs.values())), ensure_ascii=False))


if __name__ == '__main__':
    main()
