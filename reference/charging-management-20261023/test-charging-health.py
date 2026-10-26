"""Targeted rejection tests for the read-only health observer's acceptance."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('charging_health', ref / 'charging-health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
sample = {'shadow': 0, 'valid': 1, 'online': 1, 'protection_ok': 1, 'budget_ua': 1500000,
          'temp_decic': 280, 'pack_uv': 8658000, 'cell1_uv': 4329000, 'cell2_uv': 4329000,
          'fault': 0, 'session_seconds': 200, 'desired_enable': 1, 'error': 0,
          'stop_error': 0, 'latched': 0, 'source_inhibit': 0, 'age_ms': 562}
limits = {'input_current_limit': 900000, 'constant_charge_current': 250000,
          'constant_charge_voltage': 8725000}
baseline = {'samples': [{'telemetry': sample, 'state': 'managed', 'charger_status': 'Full',
                         'battery': {'current_now': '-10000'}}],
            'same_boot': True, 'taint_before': 0, 'taint_after': 0,
            'limits_before': limits, 'limits_after': limits,
            'native_allowance_before': 100000, 'native_allowance_after': 100000,
            'fault_delta': {key: 0 for key in health.FAULTS},
            'camera_and_four_services_unchanged': True,
            'manifest_sha256': 'fixture', 'duration_seconds': 120}
cases = 0
assert health.audit(baseline)['passed']  # Full or net discharge is not a fake fault.
cases += 1
for delta, expected in [({'shadow': 1}, 'shadow'), ({'latched': 1}, 'fault'),
                        ({'stop_error': -5}, 'fault'), ({'fault': 1}, 'fault'),
                        ({'source_inhibit': 1, 'error': -61, 'valid': 0}, 'waiting_source'),
                        ({'source_inhibit': 1, 'latched': 1}, 'fault'),
                        ({'error': -5}, 'fault'), ({'valid': 0}, 'unavailable'),
                        ({'protection_ok': 0}, 'unavailable'), ({'online': 0}, 'detached'),
                        ({'age_ms': -1}, 'stale'), ({'age_ms': 3001}, 'stale'),
                        ({'desired_enable': 0}, 'inhibited'), ({'age_ms': 3000}, 'managed')]:
    value = dict(sample, **delta)
    assert health.classify(value) == expected, delta
    data = copy.deepcopy(baseline)
    data['samples'] = [{'telemetry': value, 'state': expected}]
    assert health.audit(data)['passed'] == (expected == 'managed')
    cases += 1
for delta in [{'same_boot': False}, {'taint_before': 512}, {'taint_after': 512},
              {'camera_and_four_services_unchanged': False}, {'samples': []},
              {'native_allowance_after': {'errno': 61}}, {'native_allowance_after': 0},
              {'limits_after': dict(limits, input_current_limit=1000000)}]:
    data = copy.deepcopy(baseline); data.update(delta)
    assert not health.audit(data)['passed']; cases += 1
for key in health.FAULTS:
    data = copy.deepcopy(baseline); data['fault_delta'][key] = 1
    assert not health.audit(data)['passed']; cases += 1
data = copy.deepcopy(baseline)
data['samples'].append({'state': 'managed', 'telemetry': dict(sample, session_seconds=199)})
assert health.audit(data)['session_counter_regressions'] == 1
assert not health.audit(data)['passed']; cases += 1
data['samples'][1]['telemetry']['session_seconds'] = 201
assert health.audit(data)['passed']; cases += 1
text = ' '.join(key + '=' + str(value) for key, value in sample.items())
assert health.parse_telemetry(text) == sample; cases += 1
for text in [text + ' valid=1', 'valid=1', 'invalid', text.replace('age_ms=562', 'age_ms=?')]:
    try:
        health.parse_telemetry(text)
    except ValueError:
        cases += 1
    else:
        raise AssertionError('bad telemetry accepted')
with tempfile.TemporaryDirectory() as temporary:
    supplies = Path(temporary)
    assert health.find_battery(supplies) is None; cases += 1
    usb = supplies / 'samurai-usb-input'; usb.mkdir(); (usb / 'type').write_text('USB\n')
    assert health.find_battery(supplies) is None; cases += 1
    for name in ['bq28z610-0', 'bq27xxx-0', 'battery']:
        battery = supplies / name; battery.mkdir(); (battery / 'type').write_text('Battery\n')
        assert health.find_battery(supplies) == battery; cases += 1
        (battery / 'type').unlink(); battery.rmdir()
    for name in ['first', 'second']:
        battery = supplies / name; battery.mkdir(); (battery / 'type').write_text('Battery\n')
    assert health.find_battery(supplies) is None; cases += 1
report = {'passed': True, 'cases': cases, 'scope': 'Actual observer classification, acceptance and Battery discovery; synthetic fault states/files, no device access',
          'tested_files': {n: hashlib.sha256((ref / n).read_bytes()).hexdigest()
                           for n in ['charging-health.py', 'test-charging-health.py']}}
(ref / 'health-observer-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
