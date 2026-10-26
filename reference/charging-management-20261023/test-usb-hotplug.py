"""Acceptance rejection tests; no device or control operations."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hotplug', ref / 'usb-hotplug.py')
hotplug = importlib.util.module_from_spec(spec); spec.loader.exec_module(hotplug)

def row(t, source='CDP'):
    offline = source == 'none'
    budget = 0 if offline else 100000 if source == 'SDP' else 1500000
    return {'t': t, 'telemetry': {'valid': 1, 'online': int(not offline), 'protection_ok': 1,
            'desired_enable': int(not offline), 'shadow': 0, 'age_ms': 500, 'error': 0,
            'stop_error': 0, 'latched': 0, 'source_inhibit': 0, 'fault': 0,
            'budget_ua': budget, 'session_seconds': 0 if offline else t + 1000 if t < 3 else t - 14},
            'source': {'online': int(not offline), 'current_max': budget,
                       'input_current_limit': 100000, 'usb_type': '[' + source + ']'},
            'registers': {'00': 2 if source == 'SDP' else 18, '0f': 2 if source == 'SDP' else 18,
                          '02': 5, '04': 0x68, '08': 8 if offline else 16, '13': 0 if offline else 2},
            'udc_state': 'not attached' if offline else 'configured'}

baseline = {'samples': [*(row(t) for t in range(3)), *(row(t, 'none') for t in range(3, 14)),
                        *(row(t, 'SDP') for t in range(14, 31))],
            'same_boot': True, 'taint_before': 0, 'taint_after': 0,
            'fault_delta': {'WARNING:': 0}, 'camera_and_four_services_unchanged': True,
            'manifest_before': 'fixture', 'manifest_after': 'fixture',
            'duration_seconds': 31, 'terminal_reason': 'reconnected_stable'}
cases = 0
result = hotplug.audit(baseline)
assert result['passed'] and result['physical_sdp_budget_accepted']
assert result['actual_input_after_ua'] == result['native_allowance_after_ua'] == 100000
cases += 1
data = copy.deepcopy(baseline)
data['samples'][14:] = [row(t) for t in range(14, 31)]
assert hotplug.audit(data)['passed'] and not hotplug.audit(data)['physical_sdp_budget_accepted']; cases += 1
for key, value in [('same_boot', False), ('taint_after', 512), ('camera_and_four_services_unchanged', False),
                   ('manifest_after', 'different')]:
    data = copy.deepcopy(baseline); data[key] = value
    assert not hotplug.audit(data)['passed']; cases += 1
data = copy.deepcopy(baseline); data['fault_delta']['WARNING:'] = 1
assert not hotplug.audit(data)['passed']; cases += 1
for field, value in [('valid', 0), ('desired_enable', 0), ('error', -5), ('stop_error', -5),
                     ('latched', 1), ('source_inhibit', 1), ('fault', 1), ('age_ms', 4000),
                     ('session_seconds', 1500)]:
    data = copy.deepcopy(baseline)
    for item in data['samples'][14:]: item['telemetry'][field] = value
    assert not hotplug.audit(data)['passed'], field
    cases += 1
for field, value in [('00', 18), ('0f', 18), ('08', 8), ('02', 6), ('04', 0x7e)]:
    data = copy.deepcopy(baseline)
    for item in data['samples'][14:]: item['registers'][field] = value
    assert not hotplug.audit(data)['passed'], field
    cases += 1
data = copy.deepcopy(baseline)
for item in data['samples'][3:14]: item['registers']['08'] = 16
assert not hotplug.audit(data)['passed']; cases += 1
data = copy.deepcopy(baseline)
for item in data['samples'][14:]: item['source']['input_current_limit'] = {'errno': 61}
assert not hotplug.audit(data)['passed']; cases += 1
data = copy.deepcopy(baseline); data['samples'] = data['samples'][:2] + data['samples'][14:]
assert not hotplug.audit(data)['passed']; cases += 1
data = copy.deepcopy(baseline); data['samples'] = [row(t, 'SDP') for t in range(31)]
result = hotplug.audit(data)
assert not result['passed'] and not result['physical_sdp_budget_accepted']; cases += 1
report = {'passed': True, 'cases': cases, 'scope': 'Actual hotplug acceptance, synthetic samples; no hardware claims',
          'tested_files': {name: hashlib.sha256((ref / name).read_bytes()).hexdigest()
                           for name in ['usb-hotplug.py', 'test-usb-hotplug.py']}}
(ref / 'usb-hotplug-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
