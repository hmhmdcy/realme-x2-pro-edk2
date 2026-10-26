"""Archive-aware R2 freeze. No test, entrypoint, transport or device execution."""
from pathlib import Path
import ast, difflib, hashlib, json
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
history = HERE / 'history/revision-1'
prior_raw = (history / 'delivery.json').read_bytes()
assert sha(prior_raw) == '93b0bc012d8f65321779863258b900b2820fa10818054cc3b53954f009ab6f86'
prior = json.loads(prior_raw); layout = json.loads((HERE / 'archive-layout.json').read_bytes())
assert layout['original_delivery_sha256'] == sha(prior_raw) and set(layout['raw_originals']) == set(prior['files'])
for name, item in prior['files'].items():
    mapped = layout['raw_originals'][name]
    assert mapped['sha256'] == item['sha256'] and mapped['bytes'] == item['bytes']
    assert sha((HERE / mapped['stored_path']).read_bytes()) == item['sha256']
    if name not in ('controller.py', 'README.md'):
        assert sha((HERE / name).read_bytes()) == item['sha256'], 'unrelated R1 file changed: ' + name
old = (history / 'controller.py').read_text(); new = (HERE / 'controller.py').read_text()
def functions(source):
    return {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
before, after = functions(old), functions(new)
assert set(before) == set(after)
changed = [name for name in before if before[name] != after[name]]
assert set(changed) == {'ssh_worker', 'terminal_job'}
restored = new
for name in changed:
    assert restored.count(after[name]) == 1
    restored = restored.replace(after[name], before[name], 1)
assert restored == old, 'code outside the two functions changed'
test = json.loads((HERE / 'close-r2-result.json').read_bytes())
assert test['passed'] is True and test['methods'] == 3 and test['default_controller']['returncode'] == 0
assert test['old_R1_12_device_13_31_suites_rerun'] is False
for name, digest in test['tested_files'].items(): assert sha((HERE / name).read_bytes()) == digest, name
scope = dict(revision=2, previous_delivery_sha256=sha(prior_raw), changed_functions=changed,
    current_function_sha256={name: sha(after[name].encode()) for name in changed},
    unchanged_controller_functions={name: sha(after[name].encode()) for name in after if name not in changed},
    code_outside_changed_functions_byte_identical=True,
    remote_supervisor_workers_contract_unchanged=True, new_cleanup_methods=3,
    inherited_R1_methods=12, inherited_R1_default_entries=3, old_suites_rerun=False,
    context_compatibility='R1 actual export_context/operator result inherited; export_context bytes and seven-raw schema unchanged; new cleanup sidecar gates terminal_job only',
    default_controller_R2_terminal0=test['default_controller'])
(HERE / 'revision-2-scope.json').write_text(json.dumps(scope, indent=2) + '\n', newline='\n')
(HERE / 'revision-1-to-2.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='R1/controller.py', tofile='R2/controller.py')), newline='\n')
names = sorted(p for p in HERE.rglob('*') if p.is_file() and p != HERE / 'delivery.json' and '__pycache__' not in p.parts)
delivery = dict(schema=prior['schema'], passed=True, frozen=True, source_only=True, revision=2,
    previous_delivery_sha256=sha(prior_raw), device_workers_delivery_sha256=prior['device_workers_delivery_sha256'],
    device_contract_sha256=prior['device_contract_sha256'], stage_proof_sha256=prior['stage_proof_sha256'],
    operator_delivery_sha256=prior['operator_delivery_sha256'], postboot_host_R2_delivery_sha256=prior['postboot_host_R2_delivery_sha256'],
    new_cleanup_methods=3, inherited_R1_methods=12, old_R1_12_device_13_31_suites_rerun=False,
    original_context_compatibility_inherited_by_byte_identity=True, actual_R2_controller_default_terminal0=True,
    actual_runtime_material_generated=False, device_SSH_USB_PM_build_SDK_Git=False,
    files={p.relative_to(HERE).as_posix(): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size) for p in names})
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n', newline='\n')
print(json.dumps(dict(frozen=True, revision=2, delivery_sha256=sha((HERE / 'delivery.json').read_bytes()),
    controller_sha256=sha((HERE / 'controller.py').read_bytes()), close_test_result_sha256=sha((HERE / 'close-r2-result.json').read_bytes()),
    scope_sha256=sha((HERE / 'revision-2-scope.json').read_bytes()), files=len(names))))
