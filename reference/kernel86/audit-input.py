"""Offline input capture audit. No hardware access or configuration change."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import re
import tarfile

OUT = Path('/mnt/e/edk2-samurai-out/kernel86')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
raw_gz = (OUT / 'input-raw.tar.gz').read_bytes()
assert sha(raw_gz) == 'a690c453fbb46055d43e3723a20ce7304c5d83e6a50791ad47f48b57bda34b0c'
raw_tar = gzip.decompress(raw_gz)
assert sha(raw_tar) == '8269842d192708cc26ec29a7ec2f84e1196c9385ebc0ed68e48c3bd4b9f9becf'
suffixes = ['before-state', 'before-dmesg', 'before-registers', 'usb-state', 'refusal',
            'sample1', 'sample2', 'after-registers', 'after-state', 'after-dmesg', 'hashes']
expected = {'tmp/k86-input-' + suffix + '.txt' for suffix in suffixes}
with tarfile.open(fileobj=io.BytesIO(raw_tar)) as tar:
    members = tar.getmembers()
    assert len(members) == len(expected) and {member.name for member in members} == expected
    assert all(member.isfile() and member.size < 5000000 for member in members)
    data = {member.name: tar.extractfile(member).read() for member in members}
checked = set()
for line in data['tmp/k86-input-hashes.txt'].decode().splitlines():
    digest, path = line.split('  ', 1)
    name = path.removeprefix('/')
    assert name in expected and name not in checked
    assert sha(data[name]) == digest
    checked.add(name)
assert checked == expected - {'tmp/k86-input-hashes.txt'}
for name, raw in data.items():
    target = OUT / Path(name).name.removeprefix('k86-')
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)

def text(suffix):
    return data['tmp/k86-input-' + suffix + '.txt'].decode()

states = {}
for suffix in ['before-state', 'after-state']:
    raw = text(suffix)
    assert 'f02d218a-cc7d-4b92-8858-c8eeaeab5777' in raw and '#85 SMP PREEMPT' in raw
    assert re.search(r'^0$', raw, re.M)
    assert 'frame_done_cnt:0mode:' in raw and 'underrun:       0' in raw
    assert '\n1\nsnapshot:count=1\n' in raw
    values = dict(re.findall(r'^(POWER_SUPPLY_\w+)=(.*)$', raw, re.M))
    assert values['POWER_SUPPLY_CAPACITY'] == '99'
    assert values['POWER_SUPPLY_CURRENT_NOW'] == '0'
    assert values['POWER_SUPPLY_STATUS'] == 'Not charging'
    states[suffix] = {'uptime_seconds': float(re.search(r'^(\d+\.\d+) \d+\.\d+$', raw, re.M)[1]),
                      'taint': 0, 'display_timeouts': 0, 'display_underruns': 0,
                      'snapshot_remaining_count': 1, 'power_supply': values}
assert states['after-state']['uptime_seconds'] - states['before-state']['uptime_seconds'] >= 5
samples = []
for suffix in ['sample1', 'sample2']:
    raw = text(suffix)
    pairs = [(int(reg, 16), int(value, 16)) for reg, value in
             re.findall(r'^reg=0x([0-9a-f]{2}) value=0x([0-9a-f]{2})$', raw, re.M)]
    assert [reg for reg, value in pairs] == [0x0b, 0x13, 0x1c, 0x1d, 0x1e, 0x1f, 0x13, 0x0b]
    values = [value for reg, value in pairs]
    assert values[0] == values[7] == 0 and values[1] == values[6] == 0x0f
    assert 'reader_exit=0' in raw and 'ADC_freshness_verified=0' in raw
    voltage_code, current_code = values[3] * 4 + (values[2] >> 6), values[5] * 4 + (values[4] >> 6)
    assert f'tentative_mV={voltage_code * 25}' in raw and f'tentative_uA={current_code * 6250}' in raw
    # MPS Rev1.0 p43, not the inverted ACOK constants in the OEM header.
    samples.append({'raw_pairs': pairs, 'status': values[1], 'VIN_power_good': bool(values[1] & 2),
                    'charge_status_code': (values[1] >> 2) & 3,
                    'charge_status': 'termination', 'voltage_code': voltage_code,
                    'OEM_scaled_input_mV': voltage_code * 25,
                    'OEM_scaled_input_uA': current_code * 6250,
                    'query_span_ns': int(re.search(r'query_span_ns=(\d+)', raw)[1]),
                    'external_calibration_verified': False, 'simultaneous_ADC_channels_verified': False})
assert [sample['OEM_scaled_input_mV'] for sample in samples] == [4525, 4525]
assert [sample['OEM_scaled_input_uA'] for sample in samples] == [281250, 250000]
assert text('refusal') == 'Refusing non-QUP1 adapter\nreader_exit=2\n'
assert text('before-registers') == text('after-registers')
baseline = (Path(__file__).parent.parent / 'kernel85/chemistry-mp2650.txt').read_text()
assert text('before-registers') == baseline
for suffix in ['before-dmesg', 'after-dmesg']:
    assert not re.search(r'(?i)\bBUG:|\bOops:|kernel panic|frame done timeout', text(suffix))
usb = text('usb-state').splitlines()
assert usb[:7] == ['configured', 'high-speed', 'super-speed-plus', '0', '0', '100', '0x80']
result = {'audit': 'PASS', 'device_members_hashed': len(checked), 'raw_members_preserved': len(data),
          'states': states, 'samples': samples, 'MP2650_fixed_reads': 40,
          'configuration_data_writes': 0, 'ADC_enable_writes': 0, 'fault_register_reads': 0,
          'USB': {'state': usb[0], 'current_speed': usb[1], 'maximum_speed': usb[2],
                  'configfs_MaxPower_mA': 100, 'bmAttributes': '0x80',
                  'typec_and_role_class_instances': 0, 'source_budget_verified': False},
          'OEM_VIN_POWER_GOOD_constants_reversed_against_MPS_p43': True,
          'calibrated_input_meter_verified': False, 'charging_rate_verified': False,
          'charge_control_or_protection_verified': False,
          'wire_includes_single_register_selector_writes': True,
          'PDF_download_completed': False, 'PDF_visual_layout_verified': False}
(OUT / 'input-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: 11 raw members/10 device hashes; two input samples; config unchanged; current driver/calibration/budget acceptance remains incomplete.')
print('Input mV/uA:', [(sample['OEM_scaled_input_mV'], sample['OEM_scaled_input_uA']) for sample in samples])
