"""Freeze the two offline artifacts as one candidate; never stages or installs."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01')
NATIVE = Path('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dt = json.loads((HERE / 'dt-result.json').read_bytes())
ko = json.loads((HERE / 'ko-result.json').read_bytes())
binding = json.loads((HERE / 'binding-result.json').read_bytes())
tools = json.loads((HERE / 'build-tools-result.json').read_bytes())
assert dt['passed'] and ko['passed'] and binding['passed'] and tools['passed']
assert dt['script_sha256'] == sha(HERE / 'compile-dt.py')
assert ko['builder_sha256'] == sha(HERE / 'build-ko.py')
assert ko['DT_result_sha256'] == sha(HERE / 'dt-result.json')
assert binding['DT_receipt_sha256'] == sha(HERE / 'dt-result.json')
assert ko['before'] == ko['after'] and not ko['diagnostics']
assert ko['intree'] == 'Y' and ko['ELF_machine'] == 'AArch64'
assert ko['actual_config_values_exact_Image502'] and ko['generated_autoconf_exact_Image502']
assert ko['imports_all_from_Image502_builtin'] and ko['unresolved_strong_imports'] == []
assert ko['strong_import_count'] == 44 and ko['Image502_export_count'] == 15097
assert all(command['terminal'] and command['returncode'] == 0 for command in [*dt['commands'], *ko['commands']])
assert ko['phases'][0]['target'] == 'modules_prepare'
assert ko['phases'][1]['target'] == 'drivers/power/supply/samurai-usb-input.ko'
image = REF / 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json'
assert sha(image) == ko['Image502_build_receipt_sha256']
assert sha(NATIVE) == dt['source_native_sha256']
candidate = PRIVATE / 'samurai-usb-input-irq-native-private.dtb'
module = PRIVATE / 'samurai-usb-input-irq-private.ko'
assert sha(candidate) == dt['candidate_DTB_sha256'] and candidate.stat().st_size == dt['candidate_DTB_bytes']
assert sha(module) == ko['module_sha256'] and module.stat().st_size == ko['module_bytes']
spec = importlib.util.spec_from_file_location('pair_fdt', HERE / 'inspect-dtb.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
old, new = parser.decode(NATIVE.read_bytes()), parser.decode(candidate.read_bytes())
assert len(old['nodes']) == 965 and len(new['nodes']) == 966
assert set(new['nodes']) - old['nodes'].keys() == {dt['only_added_node']}
assert all(new['nodes'][path] == props for path, props in old['nodes'].items())
assert all(new[key] == old[key] for key in ['reserves', 'boot_cpu', 'version', 'last_version'])
overlay = next(node.value.value for node in ast.parse((HERE / 'compile-dt.py').read_text()).body
               if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'OVERLAY' for target in node.targets))
(HERE / 'board-irq-overlay.dtso').write_bytes(overlay.encode())
assert sha(HERE / 'board-irq-overlay.dtso') == dt['overlay_source_sha256']
initial = HERE / 'history/plan-01'
initial_plan = json.loads((initial / 'plan.json').read_bytes())
assert sha(initial / 'plan.json') == 'df8962559b94aae91c776d0ef4a096d346b37af4e9398da005f15bb5ceee4e27'
assert all(sha(initial / name) == digest for name, digest in initial_plan['files'].items())
receipts = {name: sha(HERE / name) for name in ['dt-result.json', 'ko-result.json', 'binding-result.json', 'build-tools-result.json']}
pair = {
    'schema': 'samurai-usb-input-IRQ-offline-board-pair-v1',
    'candidate_id': 'usb-input-irq-board-01',
    'status': 'offline_DT_and_module_passed_not_installed',
    'required_together': True,
    'new_DTB_must_not_be_used_with_old_R7_module': True,
    'runtime_deployment_guard_or_cohort': False,
    'native_DTB': {'private_path': str(candidate), 'sha256': sha(candidate), 'bytes': candidate.stat().st_size,
                   'source_native_sha256': sha(NATIVE)},
    'USB_module': {'private_path': str(module), 'sha256': sha(module), 'bytes': module.stat().st_size,
                   'intree': 'Y', 'release': ko['release'], 'source_sha256': ko['source_sha256'],
                   'decoder_sha256': ko['decoder_sha256'], 'imports_against_Image502': True},
    'Image502_reference': {'sha256': '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
                           'build_receipt_sha256': sha(image), 'not_rebuilt_for_this_pair': True},
    'receipts': receipts,
    'physical_IRQ_acceptance_required': [
        'Same new native DT and provider instance actually probed',
        'Both named usbin-plugin and usbin-src-change IRQs actually registered',
        'Physical detach/attach changes corresponding IRQ counts and event times',
        'Protection, source budget, native allowance and hardware limits remain correct',
        'Both optional IRQ lookups absent can fall back to legacy polling: loading alone is insufficient',
    ],
    'physical_IRQ_or_latency_accepted': False,
    'APSD_PD_role_route_permission_granted': False,
    'boot_firmware_FAT_BDS_Image_or_rootfs_changed': False,
}
(HERE / 'pair-manifest.json').write_text(json.dumps(pair, indent=2) + '\n')
(PRIVATE / 'pair-manifest.json').write_bytes((HERE / 'pair-manifest.json').read_bytes())
execution = {'passed': True, 'DT_exec_returncode': 0, 'module_native_exec_session': 59826,
             'module_exec_returncode': 0, 'module_child_PIDs': [row['pid'] for row in ko['commands']],
             'same_original_module_exec_handle_waited': True,
             'all_recorded_tool_processes_terminal': True, 'old16_function_cases_rerun': False,
             'old_R7_and_Image502_and_shared_tracked_inputs_unchanged': True,
             'original284_Ubuntu_root_guard_used': True,
             'active_make_compiler_storage_process_remaining': False,
             'unmounted_or_new_anchor': False, 'device_SDK_Git_used': False}
(HERE / 'execution-receipt.json').write_text(json.dumps(execution, indent=2) + '\n')
current_plan = {'status': 'approved_minimal_plan_executed_offline_passed',
                'initial_plan_packet': 'history/plan-01/plan.json',
                'initial_plan_sha256': sha(initial / 'plan.json'),
                'pair_manifest_sha256': sha(HERE / 'pair-manifest.json'), 'receipt_sha256': receipts}
(HERE / 'plan.json').write_text(json.dumps(current_plan, indent=2) + '\n')
delivery = {'schema': 'samurai-usb-input-IRQ-board-delivery-v1', 'passed': True, 'frozen': True,
            'pair_manifest_sha256': sha(HERE / 'pair-manifest.json'),
            'native_DTB_sha256': sha(candidate), 'USB_module_sha256': sha(module),
            'files': {str(path.relative_to(HERE)).replace('\\', '/'): sha(path)
                      for path in sorted(HERE.rglob('*')) if path.is_file() and path.name != 'delivery.json'},
            'receipt_sha256': receipts, 'device_accepted': False,
            'new_boot_or_R9_deployment_cohort_prepared': False}
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n')
print(json.dumps({'passed': True, 'delivery_sha256': sha(HERE / 'delivery.json'),
                  'pair_sha256': sha(HERE / 'pair-manifest.json'), 'receipts': receipts,
                  'DTB': sha(candidate), 'ko': sha(module)}))
