"""Read retained source/receipts only; no imported runtime entry or device tools."""
from pathlib import Path
import ast
import base64
import gzip
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
POST = REF / 'charging-management-20261023/image501-postboot-readonly'
ADOPT = REF / 'charging-session-20261023/gauge-image501-adoption-candidate'
ICON = REF / 'charging-session-20261023/icon-capture-image501-candidate'
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001')
OLD = PRIVATE / 'postboot-r1-03-private'
NEW = PRIVATE / 'postboot-r1-04-private'
sha = lambda data: hashlib.sha256(data).hexdigest()
digest = lambda path: sha(path.read_bytes())
read = lambda path: json.loads(path.read_bytes())

def functions(data):
    text = data.decode()
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

def delivery(directory):
    result = read(directory / 'delivery.json')
    for name, pin in result['files'].items():
        assert digest(directory / name) == pin['sha256'], name
    return digest(directory / 'delivery.json')

source = (POST / 'device.py').read_bytes()
assert sha(source) == 'be1b56a1fe38fd46cd8c58e303a8d98c38b6fd154b8db0a32231095b97418eea'
executed = (NEW / 'executed-device-source.py').read_bytes()
assert executed.endswith(source)
prefix = executed[:-len(source)].decode()
node = next(n for n in ast.parse(prefix).body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'POSTBOOT_REQUEST' for t in n.targets))
request = json.loads(base64.b64decode(ast.literal_eval(node.value.args[0].args[0])))
old_body = (OLD / 'executed-device-source.py').read_bytes().split(b'\n', 1)[1]
assert sha(old_body) == 'c49046da0d55d29102403495da7a496a98067c806d4e2ec2b52de184092bdf4f'
old_functions, new_functions = functions(old_body), functions(source)
changed = [name for name in new_functions if new_functions[name] != old_functions[name]]
assert changed == ['check_gauge']

codec = read(NEW / 'codec-private.json')
wire_source = (NEW / 'transport-codec-private.py').read_bytes()
embedded = [n.value for n in ast.walk(ast.parse(wire_source.decode()))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and len(n.value) > 10000]
assert len(embedded) == 1 and base64.b64decode(embedded[0]) == executed
wire_stdout = (NEW / 'transport-stdout-private.b64').read_bytes()
stdout = (NEW / 'stdout-private.json').read_bytes()
assert gzip.decompress(base64.b64decode(wire_stdout)) == stdout
assert codec['exact_payload_sha256'] == sha(executed)
assert codec['wire_source_sha256'] == sha(wire_source)
assert codec['decoded_stdout_sha256'] == sha(stdout)
assert codec['wire_stdout_sha256'] == sha(wire_stdout)
assert codec['returncode'] == 0
record, receiver = json.loads(stdout), read(NEW / 'receiver-result-private.json')
result, raw = record['result'], record['raw']
assert result['passed'] is True and result['errors'] == {} and len(result['checks']) == 9
assert receiver['passed'] is True and receiver['transport_exit'] == 0
assert len(receiver['checks']) == 9 and all(receiver['checks'].values())
assert raw['identity_before']['boot_id'] == raw['identity_after']['boot_id'] != request['guard']['boot_id']
assert raw['identity_before']['uname']['version'].startswith('#501 ')
assert int(raw['identity_before']['taint']) == 0
assert raw['source'] == {'online': '1', 'usb_type': 'Unknown SDP DCP [CDP] C',
                        'current_max': '1500000', 'input_current_limit': '500000'}
assert raw['charger']['input_current_limit'] == '900000'
assert raw['charger']['constant_charge_current'] == '250000'
assert raw['charger']['constant_charge_voltage'] == '8725000'
assert raw['gauge'] == {'flag': 'Y', 'status': 'Discharging', 'current_now': '-70000', 'current_avg': '-1000'}
assert result['checks']['charging']['state'] == ['healthy_full_charge_only_hold'] * 2
mode = result['checks']['instant_gauge']
assert mode['source_type'] == 'CDP' and mode['source_budget_ua'] == 1500000
assert mode['hardware_input_ua'] == 900000 and mode['SDP_hardware500_observed'] is False
assert mode['startup500_descriptor_and_native500_preserved'] is True
assert mode['pixel_or_physical_latency_accepted'] is False
telemetry = []
for field in ['telemetry_before', 'telemetry_after']:
    t = dict(x.split('=', 1) for x in raw[field].split())
    assert all(int(t[k]) == 0 for k in ['fault', 'error', 'stop_error', 'latched', 'source_inhibit',
           'thermal_inhibit', 'cycle_timeout', 'gauge_charge_stop', 'desired_enable'])
    assert all(int(t[k]) == 1 for k in ['valid', 'online', 'protection_ok', 'logical_full',
                                     'full_holding', 'hold_requested'])
    assert int(t['full_cause']) == 3
    telemetry.append({k: int(t[k]) for k in ['temp_decic', 'pack_uv', 'cell1_uv', 'cell2_uv',
                                           'full_cause', 'desired_enable', 'gauge_current_ua']})
old_record = read(OLD / 'stdout-private.json')
assert old_record['result']['passed'] is False

test = read(POST / 'test-result.json')
assert test['passed'] and test['case_count'] == 10
assert test['device_sha256'] == sha(source)
assert test['payload_sha256'] == digest(POST / 'payload.py')
assert test['test_sha256'] == digest(POST / 'test-delta.py')
adoption_delivery = delivery(ADOPT)
assert digest(ADOPT / 'adopt.py') == 'e689b8900e926eacfd045d7a893042afaf65290f727f630239c5f3c5752fd7a7'
pins = read(ADOPT / 'source-pins.json')
old_pins = read(ADOPT / 'before-cdp-profile/source-pins.json')
assert [k for k in pins if pins[k] != old_pins[k]] == ['postboot_device']
assert pins['postboot_device']['sha256'] == sha(source)
adopt_test = read(ADOPT / 'test-cdp-binding-result.json')
assert adopt_test['passed'] and adopt_test['old_actual_report_still_failed']
assert adopt_test['delegate_device_sha256'] == sha(source)
assert adopt_test['root_new_test_receipt_sha256'] == digest(POST / 'test-result.json')
assert adopt_test['cached_input_sha256'] == digest(OLD / 'stdout-private.json')
icon_delivery = delivery(ICON)
icon_old = (ICON / 'before-cdp-profile/launcher.py').read_bytes()
icon_new = (ICON / 'launcher.py').read_bytes()
assert icon_new.replace(b'startup500_descriptor_and_native500_preserved',
                       b'startup500_native_and_hardware500_preserved') == icon_old
template = read(ICON / 'template-test-result.json')
assert template['passed'] and template['launcher_sha256'] == sha(icon_new)
for name, pin in template['files'].items(): assert digest(ICON / name) == pin

review = {
    'scope': 'narrow SDP/CDP postboot classification and dependent profile changes; retained actual 04 evidence',
    'no_blocker_in_reviewed_delta': True,
    'postboot_source_sha256': sha(source), 'only_changed_postboot_function': changed,
    'ten_case_receipt_sha256': digest(POST / 'test-result.json'),
    'actual04': {
        'stdout_sha256': sha(stdout), 'exact_executed_payload_sha256': sha(executed),
        'codec_sha256': digest(NEW / 'codec-private.json'),
        'receiver_sha256': digest(NEW / 'receiver-result-private.json'),
        'wire_decodes_to_exact_stdout': True, 'embedded_payload_equals_executed_file': True,
        'executed_body_equals_frozen_be1b': True, 'transport_exit': 0,
        'nine_checks_passed': True, 'same_new_501_boot_before_after': True, 'taint': 0,
        'source_type': 'CDP', 'source_budget_ua': 1500000, 'descriptor_ma': 500,
        'native_input_ua': 500000, 'hardware_input_ua': 900000,
        'CC_ua': 250000, 'CV_pack_uv': 8725000,
        'gauge': raw['gauge'], 'telemetry': telemetry,
        'safe_Full_hold_accepted_without_charging_claim': True,
        'physical_or_pixel_latency_accepted': False},
    'old03_failed_original_retained': {'stdout_sha256': digest(OLD / 'stdout-private.json'), 'passed': False},
    'adoption': {'source_sha256': digest(ADOPT / 'adopt.py'), 'source_unchanged': True,
                 'source_pins_sha256': digest(ADOPT / 'source-pins.json'),
                 'only_pin_changed': 'postboot_device', 'delivery_sha256': adoption_delivery,
                 'cdp_binding_receipt_sha256': digest(ADOPT / 'test-cdp-binding-result.json')},
    'collector': {'launcher_sha256': sha(icon_new), 'only_runtime_code_delta': 'verified instant-gauge report key',
                  'delivery_sha256': icon_delivery, 'template_receipt_sha256': digest(ICON / 'template-test-result.json'),
                  'SDP_or_CDP_not_fixed': True, 'ready_capture_fetch_unchanged': True},
    'comparison_limit': 'old physical capture SDP/hardware500 versus current CDP/hardware900 cannot isolate instantaneous-current effect',
    'old_suites_rerun': False, 'device_network_SDK_build_Git_access': False,
    'runtime_adoption_and_physical_capture_not_independently_reviewed_here': True
}
(HERE / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
print(json.dumps({'review_sha256': digest(HERE / 'review.json'),
                  'no_blocker': True, 'actual04_CDP_native500_hardware900': True}))
