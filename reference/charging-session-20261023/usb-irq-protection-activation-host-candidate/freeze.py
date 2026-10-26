"""Freeze actual offline source and affected checks; no runtime material."""
from pathlib import Path
import ast, hashlib, json
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
test = json.loads((HERE / 'test-result.json').read_bytes())
assert test['passed'] is True and test['methods'] == 12 and len(test['default_checks']) == 3
assert test['actual_runtime_material_generated'] is False and test['device_or_transport_accessed'] is False
assert test['old_device_13_31_suites_rerun'] is False
for name, digest in test['tested_files'].items(): assert sha((HERE / name).read_bytes()) == digest, name
pins = json.loads((HERE / 'source-pins.json').read_bytes())
for name, item in pins.items(): assert sha(Path(item['path']).read_bytes()) == item['sha256'], name
workers = REF / 'charging-session-20261023/usb-irq-protection-restart-candidate'
contract = json.loads((workers / 'prepare-contract.json').read_bytes())
assert sha((workers / 'prepare-contract.json').read_bytes()) == '13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914'
functions = {}
for name in ('controller.py', 'remote.py', 'supervisor.py'):
    raw = (HERE / name).read_bytes(); source = raw.decode(); tree = ast.parse(source)
    compile(raw, name, 'exec')
    functions[name] = {n.name: sha(ast.get_source_segment(source, n).encode()) for n in tree.body if isinstance(n, ast.FunctionDef)}
reuse = dict(byte_frozen_device_workers={name: pins[key]['sha256'] for key, name in [('quiesce', 'eud-quiesce.py'), ('restart', 'eud-restart.py')]},
    byte_frozen_device_common=pins['device_common']['sha256'], pure_stage_proof_sha256=pins['stage_proof']['sha256'],
    original_strict_key_source_sha256=pins['key_transport']['sha256'],
    adapted_host_sources={name: pins[name] for name in ('baseline_controller', 'baseline_remote', 'baseline_supervisor')},
    host_reuse_scope='adapted saved-job/owned-Popen/reconcile/once/7raw algorithms; no assertion that new host function bytes are unchanged',
    actual_new_functions=functions, actual_export_accepted_by_frozen_operator_context_gate=True,
    compatibility_fixture='only material/OS/transport boundaries fake; actual controller.export_context and frozen operator.validate_context executed',
    old_suites_rerun=False)
(HERE / 'source-reuse.json').write_text(json.dumps(reuse, indent=2) + '\n', newline='\n')
interface = dict(schema='samurai-usb-irq-protection-host-contract-v1', source_only=True,
    transaction_regex=contract['transaction_regex'], device_contract_sha256=pins['device_contract']['sha256'],
    actions=['bind', 'prepare', 'quiesce', 'status', 'fetch', 'inspect', 'restart'],
    bind_inputs=['actual stage host directory', 'actual stage fetch directory', 'new activation transaction'],
    host_private_base='E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-activation',
    remote_root='/root/charging-management-20261023/<activation>', remote_owner='/run/samurai-usb-irq-protection-activation-owner-private.json',
    context_schema=contract['context_schema'], context_files=contract['context_files'],
    host_only_stage_refs=contract['host_only_context_fields'],
    mutations_once=True, pending_recovery='original status/fetch and exact terminal/raw proof only; no retry/replay/cleanup',
    original_ssh_nonzero_not_syscall_success=True, fresh_fastboot_identity_separate=True,
    partitions_written_by_this_leaf=[], charging_control_or_service_stop=False,
    actual_runtime_material_generated=False)
(HERE / 'host-contract.json').write_text(json.dumps(interface, indent=2) + '\n', newline='\n')
names = sorted(p for p in HERE.iterdir() if p.is_file() and p.name != 'delivery.json')
delivery = dict(schema='samurai-usb-irq-protection-activation-host-delivery-v1', passed=True, frozen=True, source_only=True,
    revision=1, device_workers_delivery_sha256=pins['device_delivery']['sha256'],
    device_contract_sha256=pins['device_contract']['sha256'], stage_proof_sha256=pins['stage_proof']['sha256'],
    operator_delivery_sha256=pins['operator_delivery']['sha256'], postboot_host_R2_delivery_sha256=pins['postboot_host_delivery']['sha256'],
    affected_methods=12, actual_default_entries_terminal0=3, actual_export_operator_context_compatible=True,
    only_synthetic_temp_material=True, actual_runtime_material_generated=False,
    device_SSH_USB_PM_build_SDK_Git=False, old_device_13_31_suites_rerun=False,
    files={p.name: dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size) for p in names})
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n', newline='\n')
print(json.dumps(dict(frozen=True, delivery_sha256=sha((HERE / 'delivery.json').read_bytes()),
    controller_sha256=sha((HERE / 'controller.py').read_bytes()), remote_sha256=sha((HERE / 'remote.py').read_bytes()),
    supervisor_sha256=sha((HERE / 'supervisor.py').read_bytes()), test_result_sha256=sha((HERE / 'test-result.json').read_bytes()))))
