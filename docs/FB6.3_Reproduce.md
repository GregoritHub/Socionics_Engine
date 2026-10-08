# Reproduce the held delivery

[source_defined] Python 3 and its standard library run the engine and integrity checks. Node runs the existing structural inspector verifier. No browser rendering is claimed. Extract both delivery archives into the same empty directory and enter `Socionics_Research_Lab_Release_1_0_Held/`.

[source_defined] Historical archive contents are under `evidence/historical/`, retaining their original relative paths and bytes. This keeps historical failed source snapshots separate from current executable source. The old ledger's archive-member references resolve against that directory; the fresh FB6.2 references resolve against the source root.

[source_defined] Before extracting, `python3 -m zipfile -t ARCHIVE.zip` checks each ZIP's CRC. The following integrity command is run from the clean unpacked root. It verifies delivered bytes and the honest held decision, not the unsupported semantic claims.

```python
from pathlib import Path
import hashlib, json, re

root = Path.cwd()
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_mapping(path):
    mapping = read(path)
    for name, expected in mapping.items():
        assert sha(root / name) == expected, name
    return len(mapping)

source_count = verify_mapping(root / 'C7_Release_Source_SHA256_v1.json')
raw_count = verify_mapping(root / 'evidence/FB6.3/Delivered_Raw_SHA256.json')
freeze_count = verify_mapping(root / 'C7_Final_Source_Freeze_v5.json')
assert freeze_count == 1355
fb62_count = verify_mapping(root / 'evidence/FB6.2/Raw_SHA256.json')
assert fb62_count == 3465

old = read(root / 'C7_Final_Ledger_v1.json')
members = set()
for archive, member, digest, size in old['evidence_objects']:
    path = root / 'evidence/historical' / member
    assert path.stat().st_size == size and sha(path) == digest, member
    members.add(member)
assert len(members) == 739

review = read(root / 'C7_Final_Ledger_v2.json')
assert review['status'] == 'held' and review['complete_cells'] == 0
assert review['full_release_complete'] is False and review['goal_complete'] is False
assert review['phase_7_authorized'] is False and len(review['rows']) == 32
assert len({(x['route'], x['polarity']) for x in review['rows']}) == 32
finding_ids = {x['id'] for x in read(root / 'evidence/FB6.2/Release_Evidence_Findings.json')['findings']}
assert len(finding_ids) == 3
fresh_links = 0
for row in review['rows']:
    assert row['full_release_complete'] is False
    assert set(row['underlying_finding_ids']) == finding_ids
    assert {'9.8', '9.11:canonical', '9.12:reviewed-acceptance', 'amendment:5.6:forged-completion-control'} == set(row['missing_items'])
    for ref in row['fresh_evidence'].values():
        path = root / ref['member']
        assert path.stat().st_size == ref['bytes'] and sha(path) == ref['sha256']
        fresh_links += 1
assert fresh_links == 256

accepted = read(root / 'evidence/FB6.2/Accepted_Method_Inventory.json')
prior = read(root / 'evidence/FB5.6/Accepted_Method_Inventory.json')
assert len(accepted['method_ids']) == len(set(accepted['method_ids'])) == 732
assert set(accepted['method_ids']) == set(prior['method_ids'])
execution = read(root / 'evidence/FB6.2/Execution_Assessment.json')
assert execution['passed'] and execution['source_unchanged']
assert execution['required_jobs'] == 47 and execution['measurement_workers'] == 81
acceptance = read(root / 'evidence/FB6.2/Acceptance.json')
assert acceptance['passed'] is False and acceptance['execution_passed'] is True

html = (root / 'docs/HLE_Full_Crux_C7_Inspector_v3.html').read_text()
data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)[1])
assert data['reviewed_ledger_sha256'] == sha(root / 'C7_Final_Ledger_v2.json')
assert data['manifest']['passing_methods'] == 732 and data['manifest']['release_complete'] is False
for row in data['ledger']:
    final = next(x for x in review['rows'] if (x['route'], x['polarity']) == (row['name'], row['face']))
    assert row['current_evidence'] == final['fresh_evidence']
    assert row['remaining'] == final['missing_items']

result = {'passed': True, 'source_files': source_count, 'raw_files': raw_count,
          'frozen_files': freeze_count, 'fb62_files_hashed': fb62_count,
          'historical_members': len(members), 'fresh_raw_links': fresh_links,
          'held_rows': 32, 'complete_rows': 0, 'distinct_methods': 732,
          'release_complete': False, 'phase_7_authorized': False}
print(json.dumps(result, sort_keys=True))
```

[source_defined] Run the existing frozen structural inspector verifier:

```sh
node tools/verify_c7_second_inspector.cjs docs/HLE_Full_Crux_C7_Inspector_v3.html verification-output/inspector
```

[source_defined] Copy the canonical-family evidence before re-running its verifier so the delivered raw reports stay unchanged. This is an ordinary independent raw reconstruction from the clean source installation, without participant replay.

```sh
python3 -c "import shutil; shutil.copytree('evidence/FB6.2/attempt1/canonical-families', 'verification-output/canonical-families')"
python3 tools/verify_c7_canonical_families.py verification-output/canonical-families
```

[source_defined] The entire 6.2 evaluation can also be rerun into a new evidence directory using the commands in report v3. Original absolute command paths are retained as historical execution metadata; do not rewrite them to pretend the archived attempt ran elsewhere. These reproduce commands do not repair the three open release-evidence defects.
