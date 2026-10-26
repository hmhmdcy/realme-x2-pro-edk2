"""Re-audit the existing capture, without another device observation."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/health-continued')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report_path = ref / 'health-observation-result.json'
old = json.loads(report_path.read_text())
raw = private / 'observation-r1-private.json'
executed = private / 'charging-health-r1.py'
assert sha(raw) == old['private_capture_sha256']
assert sha(executed) == old['observer_sha256']
original_test = json.loads((private / 'health-observer-r1-test-result.json').read_text())
assert original_test['passed'] and original_test['tested_files']['charging-health.py'] == sha(executed)
current_test = json.loads((ref / 'health-observer-test-result.json').read_text())
assert current_test['passed'] and current_test['tested_files']['charging-health.py'] == sha(ref / 'charging-health.py')

def functions(path):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}

before, after = functions(executed), functions(ref / 'charging-health.py')
for name in ['parse_telemetry', 'classify', 'audit']:
    assert before[name] == after[name], 'Acceptance changed: ' + name
spec = importlib.util.spec_from_file_location('health', ref / 'charging-health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
data = json.loads(raw.read_text())
report = health.audit(data)
assert report['passed']
report.update({key: old[key] for key in ['observer_sha256', 'private_capture_sha256',
              'samples_are_cached_kernel_telemetry', 'configuration_or_service_writes',
              'range', 'charger_status_counts']})
report.update({'hardware_full_status_observed': all(row['charger_status'] == 'Full' for row in data['samples']),
               'cell_max_delta_uv': max(abs(row['telemetry']['cell1_uv'] - row['telemetry']['cell2_uv'])
                                        for row in data['samples']),
               're_audited_without_new_device_access': True,
               'acceptance_functions_unchanged': True,
               'audit_tool_sha256': sha(ref / 'charging-health.py'),
               'optional_battery_properties_captured': False,
               'collector_note': 'R1 did not find the bq28z610-0 battery because its optional lookup guessed bq27*. No SOC/current values are inferred. Battery-class discovery corrected and tested offline (41 cases); no repeat capture.',
               'complete_termination_recharge_cycle_accepted': False})
report_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
