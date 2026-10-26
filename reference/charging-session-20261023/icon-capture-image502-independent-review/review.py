"""Static/hash-only migration review; no author import or entry-point execution."""
from pathlib import Path
import ast
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
NEW = REF / 'charging-oem-audit-20261023/icon-capture-image502-candidate'
OLD = REF / 'charging-session-20261023/icon-capture-image501-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def funcs(path):
    text = path.read_text()
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}


def value(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(name)


delivery_raw = (NEW / 'delivery.json').read_bytes()
assert sha(delivery_raw) == 'e638bb4649d7c7d0154d9787b116c52cd500ed5cc2d9e2e5610ab28ce1b0fbd9'
delivery = json.loads(delivery_raw)
for name, row in delivery['files'].items():
    raw = (NEW / name).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], name
for row in json.loads((NEW / 'source-pins.json').read_bytes()).values():
    p = row['path']
    assert p.startswith('/mnt/e/')
    assert sha(Path('E:/' + p[len('/mnt/e/'):]).read_bytes()) == row['sha256']
test = json.loads((NEW / 'template-test-result.json').read_bytes())
assert test['passed'] and test['affected_cases'] == 14 and len(test['groups']) == 3
assert test['runtime_identity_unbound'] and test['old32_and12_not_rerun']
assert sha((NEW / 'launcher.py').read_bytes()) == test['launcher_sha256']
for name, expected in test['files'].items():
    assert sha((NEW / name).read_bytes()) == expected
assert sha((OLD / 'template-test-result.json').read_bytes()) == test['reused_501_template_receipt_sha256']
for name in ['worker.py', 'audit.py', 'baseline-test-result.json', 'bind-identity.py']:
    assert (NEW / name).read_bytes() == (OLD / name).read_bytes(), name
old_guard = '/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
new_guard = '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'
assert (NEW / 'capture-entry.py').read_bytes().replace(new_guard.encode(), old_guard.encode()) == (OLD / 'capture-entry.py').read_bytes()
old_funcs, new_funcs = funcs(OLD / 'launcher.py'), funcs(NEW / 'launcher.py')
same = {name: sha(body.encode()) for name, body in old_funcs.items() if new_funcs.get(name) == body}
assert same == test['unchanged_actual_launcher_functions']
assert {'ready_check', 'retain_fetch', 'cleanup_check', 'runtime_expected'} <= set(same)
assert value(NEW / 'launcher.py', 'REMOTE').replace('/icon-capture-image502', '/icon-capture-image501') == value(OLD / 'launcher.py', 'REMOTE')

def old_profile(text):
    replacements = [
        ('image502-notify-activation', 'image501-activation'),
        ('image502-notify-live-001', 'image501-gauge-live-001'),
        ('samurai-image502-notify-postboot-readonly-v1', 'samurai-image501-postboot-readonly-v1'),
        ('Image502', 'Image501'), ('image502', 'image501'), ('#502 ', '#501 '),
        ('ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1', '7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'),
        ('9c101bf2350c21a52d1fc0d0a204862a5ba56e9a291f6c0c2a01f847feb98a16', 'fec4b3fdef5d1433829da77109628a3e7d807b9802117657ad7a09404408c82d')]
    for source, target in replacements:
        text = text.replace(source, target)
    return text

for name in ['launcher.py', 'transport.py']:
    assert old_profile((NEW / name).read_text()) == (OLD / name).read_text(), name
identity = new_funcs['reviewed_identity']
for item in ['Image502_verified', 'samurai-image502-notify-postboot-readonly-v1', '#502 ', new_guard,
             'postboot_Image502_passed', '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
             'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1']:
    assert item in identity
assert new_funcs['run'].index('adopt_local(bundle, pins, migration)') < new_funcs['run'].index('save_new(directory / \'launch-request-private.json\'')
ready = new_funcs['ready_check']
assert 'len(observations) != 2' in ready and "b['tick'] > a['tick'] >= 3" in ready
assert 'min(remaining, deadline_remaining) - roundtrip < 130' in ready
checks = json.loads((NEW / 'local-check-result.json').read_bytes())
assert checks['passed'] and all(row['exit_code'] == 0 for row in checks['commands'])
assert checks['affected_test']['exit_code'] == 0 and not checks['runtime_identity_created']
assert not delivery['runtime_identity_pins_generated']

result = {
    'verdict': 'no_new_blocker_in_image502_profile_migration',
    'delivery_sha256': sha(delivery_raw),
    'launcher_sha256': sha((NEW / 'launcher.py').read_bytes()),
    'author_test_receipt_sha256': sha((NEW / 'template-test-result.json').read_bytes()),
    'reviewed_author_tests_not_executed': {'groups': 3, 'cases': 14},
    'unchanged_actual_launcher_functions': same,
    'worker_audit_baseline32_bind_bytes_unchanged': True,
    'capture_entry_only_guard_changed': True,
    'launcher_transport_complete_delta_only_known_profile_literals': True,
    'REMOTE_complete_delta_only_output_base': True,
    'actual_adoption_before_runtime_bind_and_launch_required': True,
    'double_fresh_heartbeat_and_130s_remaining_gate_unchanged': True,
    'total_deadline_300s_and_reconnect_observation_90s_unchanged': True,
    'original_child_cleanup_unknown_fetch_lifecycle_preserved': True,
    'no_new_stopper_desktop_UPower_or_policy_changes': True,
    'author_entrypoints_imported_or_executed': False,
    'old_tests_build_storage_device_SSH_USB_Git_used': False,
    'actual_runtime_identity_capture_cleanup_or_latency_accepted': False,
    'reviewer_sha256': sha(Path(__file__).read_bytes())
}
out = HERE / 'review-result.json'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({'verdict': result['verdict'], 'review_result_sha256': sha(out.read_bytes())}))
