"""Local hash/AST binding only; no import or execution of reviewed entrypoints."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
R1 = REF / 'charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate'
R2 = REF / 'charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def functions(path):
    text = Path(path).read_text()
    return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
            if isinstance(node, ast.FunctionDef)}

expected = {'R1_delivery': (R1 / 'delivery.json', 'f126a56b680298f54313fb2a232f84462f8a218e8647fc3e706934f097221b17'),
            'R2_delivery': (R2 / 'delivery.json', 'ee53341c31c75970df3fdbe3a417fe5042aabd3096ec8717547a87de9751c956'),
            'R1_tests': (R1 / 'test-result.json', '1a1afd91c7fe79f251586ef7d50eed0e198d02987d84c8d9377808a7d65f117f'),
            'R1_interface': (R1 / 'interface-check-result.json', 'ac2bf86682fce5c91fb6cf906d5abef162179584db4cea306d6380476eb2e05f'),
            'R2_tests': (R2 / 'test-result.json', '80677056d72383400032c7384c6bef464b4abb7dfcd745bdc031f5b61c3be411')}
for name, (path, value) in expected.items():
    need(sha(path) == value, 'review input changed: ' + name)
deliveries = {}
for name, root in [('R1', R1), ('R2', R2)]:
    delivery = json.loads((root / 'delivery.json').read_bytes())
    need(delivery['passed'] and delivery['frozen'], name + ' not frozen')
    for file, entry in delivery['files'].items():
        need(sha(root / file) == entry['sha256'] and (root / file).stat().st_size == entry['bytes'], name + ' file changed: ' + file)
    deliveries[name] = delivery

tests = json.loads((R2 / 'test-result.json').read_bytes())
need(tests['passed'] and tests['new_case_count'] == 3 and
     all(case['passed'] for case in tests['new_cases']) and
     tests['default_source_only']['terminal'] and tests['default_source_only']['returncode'] == 0, 'R2 test/default terminal evidence')
for file, value in tests['files'].items():
    need(sha(R2 / file) == value, 'new tests/source binding: ' + file)
for name, key in [('R1_delivery', 'reused_R1_delivery_sha256'), ('R1_tests', 'reused_R1_tests_sha256'),
                  ('R1_interface', 'reused_R1_interface_sha256')]:
    need(tests[key] == expected[name][1], 'R2 history reuse binding')
need((R1 / 'supervisor.py').read_bytes() == (R2 / 'supervisor.py').read_bytes(), 'supervisor changed')
unchanged = {}
for file, allowed_change in [('host.py', 'transfer'), ('remote.py', 'execute')]:
    old, new = functions(R1 / file), functions(R2 / file)
    need(set(old) == set(new), 'function set changed: ' + file)
    for name in old:
        if name != allowed_change:
            need(old[name] == new[name], 'unexpected function changed: ' + name)
            unchanged[file + ':' + name] = digest(new[name])
for name, value in tests['unchanged_functions'].items():
    need(unchanged[name] == value, 'reported reused function differs')

for file in ['host.py', 'remote.py', 'supervisor.py']:
    tree = ast.parse((R2 / file).read_text())
    forbidden = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr in ['kill', 'terminate']]
    need(not forbidden, 'unexpected child kill/terminate')
    need(not [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
              any(keyword.arg == 'timeout' for keyword in node.keywords)], 'unexpected timeout call')
host_transfer = ast.parse(functions(R2 / 'host.py')['transfer']).body[0]
guarded_communicate = [node for node in ast.walk(host_transfer) if isinstance(node, ast.Try) and
                       any(isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and
                           item.func.attr == 'communicate' for item in ast.walk(ast.Module(body=node.body, type_ignores=[])))]
need(len(guarded_communicate) == 1, 'one exact communication region')
region = guarded_communicate[0]
need(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'save'
         for node in ast.walk(ast.Module(body=region.body, type_ignores=[]))), 'process receipt not inside protected region')
need(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'wait'
         for node in ast.walk(ast.Module(body=region.finalbody, type_ignores=[]))), 'same-child wait missing from finally')

pins = json.loads((R2 / 'source-pins.json').read_bytes())
for name, entry in pins.items():
    path = Path(entry['path'])
    need(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], 'frozen source pin changed: ' + name)
need(pins['worker']['sha256'] == '47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a' and
     pins['worker_delivery']['sha256'] == '7fe11dd984756ef9d5f6a16f5488adf138d381fdbed26d408965cd28aec9bbb5', 'actual worker chain')

result = {
    'schema': 'samurai-stage-host-independent-review-v1', 'passed': True,
    'conclusion': 'No new blocking issue found in the repaired R2 scope by static source and receipt review.',
    'R1_finding_retained': 'r1-finding.json',
    'reviewer_source_sha256': sha(Path(__file__)),
    'inputs': {name: value for name, (_, value) in expected.items()},
    'R2_host_sha256': sha(R2 / 'host.py'), 'R2_remote_sha256': sha(R2 / 'remote.py'),
    'supervisor_byte_exact_R1_sha256': sha(R2 / 'supervisor.py'),
    'all_other_top_level_functions_byte_exact': unchanged,
    'existing_evidence_reviewed_not_executed': {
        'R1_actual_cases': 20, 'R1_in_memory_host_worker_interface_cases': 1,
        'R2_new_actual_cases': 3, 'R2_default_source_only_terminal_returncode': 0,
        'new_process_and_transport_boundaries_are_fake': True,
    },
    'findings': [
        'Actual complete Image502 postboot/adoption/executed-source/current-pointer/original-key endpoint gates precede runtime-directory and request creation; source-only check does not bind future identity.',
        'Remote launch writes and fsyncs the exact request before dispatch. The supervisor passes that regular file descriptor to the sole actual worker Popen, not DEVNULL or a disappearing SSH pipe.',
        'The supervisor owns the worker Popen and finally waits that exact child even after worker-receipt publication failure; its rc receipt is distinct from the SSH/parent dispatch result.',
        'R2 covers host SSH receipt publication and communicate with the same try/finally. Failure closes only the owned stdin to EOF before same-child wait, retains the original error and terminal evidence, and never replays the once intent.',
        'Status/fetch are read-only observations. On a different boot they classify source_boot_ended and avoid current PID lookup; unproved boot/guard remains unknown. A changed final identity invalidates PID attribution.',
        'Malformed parent launch-receipt is retained as read_error and raw data. It cannot authorize PID attribution, worker terminal verification, relaunch or runtime success.',
        'Launch claim and exact source/request/argv chain remain strict. No timeout-kill, retry, lease renewal, worker re-execution, module operation, evidence capture or reboot is added.',
    ],
    'limits': [
        'Static/fake-boundary evidence is not real transport, actual Image502 adoption, completed stage, activation, IRQ delivery or hardware acceptance.',
        'A lost or malformed launch receipt remains unknown; raw retrieval alone is not a qualification or recovery authorization.',
        'A future stage success still requires the actual worker result, original supervisor/worker terminal chain and all contract conditions; this host always reports runtime_validation_accepted=false.',
    ],
    'review_actions': {'author_entrypoints_imported_or_run': False, 'tests_run': False,
                       'device_SSH_USB_SDK_build_storage_Git_accessed': False,
                       'author_files_modified': False, 'runtime_request_or_guard_created': False},
}
(HERE / 'review-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'review_result_sha256': sha(HERE / 'review-result.json'),
                  'reviewed_R2_delivery_sha256': expected['R2_delivery'][1]}))
