"""Target the new kernel, pair and current-property acceptance boundaries offline."""
from pathlib import Path
import ast
import base64
import copy
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
m = module('postboot501', HERE / 'device.py')
payload = module('postboot_payload501', HERE / 'payload.py')
cases = []
def rejects(fn):
    try: fn()
    except (AssertionError, TypeError, ValueError, KeyError): return
    raise AssertionError('missing refusal')

startup = {'sha256': '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a',
           'regular': True, 'symlink': False, 'uid': 0, 'gid': 0, 'mode': 0o755}
r = {'gauge': {'flag': 'Y', 'status': 'Charging', 'current_now': '75000', 'current_avg': '-20000'},
     'eud': {'cmdline': 'console=tty0 bq27xxx_battery.samurai_instant_current=1'},
     'startup': startup, 'config_max_power_ma': '500', 'udc': {'a600000.usb': {'state': 'configured'}},
     'source': {'usb_type': '[SDP] CDP DCP', 'current_max': '500000', 'input_current_limit': '500000'},
     'charger': {'input_current_limit': '500000'}}
assert m.check_gauge(r)['flag_Y_and_exact_cmdline']
cases.append('separate_current_now_and_avg_signs_allowed_with_real_optin')
for field, value in [('flag', 'N'), ('current_avg', {'errno': 2}), ('current_now', {'errno': 5})]:
    bad = copy.deepcopy(r); bad['gauge'][field] = value
    rejects(lambda: m.check_gauge(bad))
    cases.append('reject_' + field + '_unqualified')
for cmdline in ('console=tty0', r['eud']['cmdline'] + ' bq27xxx_battery.samurai_instant_current=0'):
    bad = copy.deepcopy(r); bad['eud']['cmdline'] = cmdline
    rejects(lambda: m.check_gauge(bad))
cases.append('missing_or_ambiguous_actual_kernel_loadoption_refused')
bad = copy.deepcopy(r); bad['config_max_power_ma'] = '100'
rejects(lambda: m.check_gauge(bad))
bad = copy.deepcopy(r); bad['source']['current_max'] = '100000'
rejects(lambda: m.check_gauge(bad))
cases.append('old_descriptor_or_native_budget_refused')
bad = copy.deepcopy(r); bad['charger']['input_current_limit'] = '100000'
rejects(lambda: m.check_gauge(bad))
cases.append('lower_hardware_input_cannot_claim_500_preserved')
cdp = copy.deepcopy(r)
cdp['source']['usb_type'] = 'Unknown SDP DCP [CDP] C'
cdp['source']['current_max'] = '1500000'
cdp['charger']['input_current_limit'] = '900000'
accepted = m.check_gauge(cdp)
assert accepted['source_type'] == 'CDP' and accepted['hardware_input_ua'] == 900000
assert accepted['startup500_descriptor_and_native500_preserved'] and not accepted['SDP_hardware500_observed']
bad = copy.deepcopy(cdp); bad['source']['current_max'] = '500000'
rejects(lambda: m.check_gauge(bad))
bad = copy.deepcopy(cdp); bad['charger']['input_current_limit'] = '950000'
rejects(lambda: m.check_gauge(bad))
bad = copy.deepcopy(r); bad['charger']['input_current_limit'] = '900000'
rejects(lambda: m.check_gauge(bad))
cases.append('actual_CDP_budget_and_board_cap_separate_from_strict_SDP500')

parts = {'boot_partition': {'bytes': 100663296, 'sha256': m.CANDIDATE_BOOT},
         'logdump_partition': {'bytes': 67108864, 'sha256': m.LOGDUMP501}}
assert m.check_partitions(parts)['candidate_boot_exact']
for field, value in [('boot_partition', m.ROLLBACK_BOOT),
                     ('logdump_partition', 'aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da')]:
    bad = copy.deepcopy(parts); bad[field]['sha256'] = value
    rejects(lambda: m.check_partitions(bad))
cases.append('mixed_partition_pair_refused')

compatible = b'realme,samurai\0qcom,sm8150\0'
rootfs = {'sha256': '1'*64, 'regular': True, 'symlink': False, 'uid': 0, 'gid': 0, 'mode': 0o644}
guard = {'boot_id': '00000000-0000-0000-0000-000000000001', 'kernel_release': '7.3.0-rc6-rmx1931-samurai-k363+',
         'kernel_version': '#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'rootfs_release_sha256': '1'*64,
         'soc_serial_sha256': '2'*64, 'compatible_sha256': hashlib.sha256(compatible).hexdigest()}
identity = {'boot_id': '00000000-0000-0000-0000-000000000002', 'taint': '0', 'rootfs': rootfs,
            'serial_sha256': '2'*64, 'compatible_b64': base64.b64encode(compatible).decode(),
            'uname': {'machine': 'aarch64', 'release': guard['kernel_release'],
                      'version': '#501 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'}}
assert m.check_identity(identity, guard)['new_boot']
bad = copy.deepcopy(identity); bad['uname']['version'] = guard['kernel_version']
rejects(lambda: m.check_identity(bad, guard))
bad = copy.deepcopy(identity); bad['boot_id'] = guard['boot_id']
rejects(lambda: m.check_identity(bad, guard))
cases.append('fresh_new501_required_old363_or_same_boot_refused')

def functions(path):
    source = path.read_text()
    return {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef)}
old_path = HERE.parent.parent / 'charging-oem-audit-20261023/eud-postboot-readonly-candidate-r3/device.py'
old, new = functions(old_path), functions(HERE / 'device.py')
unchanged = ['block_fact', 'check_install', 'check_camera', 'check_producers', 'check_services',
             'healthy_charge_mode', 'module_fact']
assert all(old[name] == new[name] for name in unchanged)
assert old['check_charging'].replace("==100", "==500") == new['check_charging']
payload.check_local()
result = {'passed': True, 'case_count': len(cases), 'cases': cases, 'device_accessed': False,
          'device_sha256': m.sha((HERE / 'device.py').read_bytes()),
          'payload_sha256': m.sha((HERE / 'payload.py').read_bytes()),
          'test_sha256': m.sha(Path(__file__).read_bytes()),
          'unchanged_actual_functions': unchanged,
          'original_device_sha256': m.sha(old_path.read_bytes()),
          'boundary': 'actual new acceptance functions and read-only AST; explicit synthetic facts; no runtime pass claimed'}
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
