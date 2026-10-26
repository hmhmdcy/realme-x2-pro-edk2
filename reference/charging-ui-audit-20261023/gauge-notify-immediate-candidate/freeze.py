"""Bind this new candidate and existing baseline receipts; no build or device I/O."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((HERE / 'source-result.json').read_bytes())
test = json.loads((HERE / 'test-result.json').read_bytes())
build = json.loads((HERE / 'object-build-result.json').read_bytes())
assert source['candidate_source_sha256'] == sha(HERE / 'bq27xxx_battery.c')
assert source['patch_sha256'] == sha(HERE / 'notify-immediate.patch')
assert source['reverse_replacement_equals_501_base'] and source['original_strict_gate_byte_equal']
assert test['passed'] and test['group_count'] == 7
assert all(sha(HERE / name) == digest for name, digest in test['files'].items())
assert build['passed'] and build['terminal'] and build['returncode'] == 0
assert build['diagnostic_bytes'] == 0 and build['before'] == build['after']
assert build['test_receipt_sha256'] == sha(HERE / 'test-result.json')
assert build['build_script_sha256'] == sha(HERE / 'build-object.py')
assert all(sha(HERE / name) == digest for name, digest in build['candidate_files'].items())
receipts = [
    'charging-oem-audit-20261023/gauge-current-samurai-candidate/build-result.json',
    'charging-session-20261023/gauge-image501-repro-candidate/build-result.json',
    'charging-session-20261023/gauge-image501-repro-candidate/abi-result.json',
    'charging-session-20261023/gauge-image501-abi-provider-supplement/result.json',
    'charging-ui-audit-20261023/bottom-latency-source-plan-image501/review.json',
]
result = {
    'passed': True,
    'scope': 'single strict-profile external-power callback scheduling delta',
    'candidate_source_sha256': sha(HERE / 'bq27xxx_battery.c'),
    'patch_sha256': sha(HERE / 'notify-immediate.patch'),
    'actual_groups': 7,
    'private_object_sha256': build['object_sha256'],
    'source_receipts': {name: sha(REF / name) for name in receipts},
    'files': {str(p.relative_to(HERE)).replace('\\', '/'): sha(p)
              for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'delivery.json'},
    'baseline_ABI_receipts_reused_only': True,
    'new_Image_linked': False,
    'installed': False,
    'new_edge_latency_measured': False,
    'Phosh_or_UPower_modified': False,
}
(HERE / 'delivery.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'delivery_sha256': sha(HERE / 'delivery.json'),
                  'test_sha256': sha(HERE / 'test-result.json'),
                  'build_sha256': sha(HERE / 'object-build-result.json')}))
