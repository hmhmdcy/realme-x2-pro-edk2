"""Offline audit of fixed OEM observations; never access hardware.

Requires the private device-generated archives, checks every member hash,
and preserves raw bytes. A passing audit validates captured observations,
not charging protection, temperature calibration or charging performance.
"""
from pathlib import Path
import gzip
import hashlib
import io
import json
import re
import tarfile

OUT = Path('/mnt/e/edk2-samurai-out/kernel85')
sha = lambda data: hashlib.sha256(data).hexdigest()
archive_specs = {
    'short': ('3cde97aa1caa6e4708569410a172990cdabb7a1b331fd826b8183d5b10711452',
              '89d81564ccc3c08c2efaa83fe13f72f61c91f52425b693f50604638b21f70816',
              ['before-state', 'before-dmesg', 'before-mp2650', 'registers',
               'reader-exit', 'after-mp2650', 'after-state', 'partition-hashes',
               'after-dmesg', 'hashes']),
    'chemistry': ('811ed2d439582a4582c7d1b29879fc7820e585ea0e92370cd1e835af1f5a6a81',
                  '49ff2da7727e1d8c12d710070be737072a05951106077e0670470dc386ecd273',
                  ['before-state', 'before-dmesg', 'before-temperatures', 'query',
                   'reader-exit', 'after-temperatures', 'mp2650', 'after-state',
                   'after-dmesg', 'refusal', 'hashes']),
    'final': ('b20885ea7b57ab31a1166f738173f096cc87d4b3220feccc1294d7f4847562fe',
              '3645b2b6af4bad2e617a72802da076353d68a776ad17051eb1176be6c8a7706c',
              ['state', 'dmesg', 'trace-config', 'partition-hashes', 'hashes']),
}
captures = {}
archive_manifest = {}
for group, (gz_sha, tar_sha, suffixes) in archive_specs.items():
    raw_gz = (OUT / (group + '-raw.tar.gz')).read_bytes()
    assert sha(raw_gz) == gz_sha
    raw_tar = gzip.decompress(raw_gz)
    assert sha(raw_tar) == tar_sha
    expected = {'tmp/k85-' + group + '-' + suffix + '.txt' for suffix in suffixes}
    with tarfile.open(fileobj=io.BytesIO(raw_tar)) as tar:
        members = tar.getmembers()
        assert len(members) == len(expected)
        assert {m.name for m in members} == expected
        assert all(m.isfile() and m.size < 5000000 for m in members)
        data = {m.name: tar.extractfile(m).read() for m in members}
    hashes = data['tmp/k85-' + group + '-hashes.txt'].decode().splitlines()
    checked = set()
    for line in hashes:
        digest, remote = line.split('  ', 1)
        name = remote.removeprefix('/')
        assert name in expected and name not in checked
        assert sha(data[name]) == digest
        checked.add(name)
    assert checked == expected - {'tmp/k85-' + group + '-hashes.txt'}
    for name, raw in data.items():
        filename = Path(name).name.removeprefix('k85-')
        target = OUT / filename
        if target.exists():
            assert target.read_bytes() == raw
        else:
            target.write_bytes(raw)
        captures[filename] = raw
    archive_manifest[group] = {
        'gz_sha256': gz_sha, 'tar_sha256': tar_sha,
        'members': len(data), 'device_hashed_members_verified': len(checked),
    }

def text(name):
    return captures[name].decode()

def state(name):
    raw = text(name)
    values = dict(re.findall(r'^(POWER_SUPPLY_\w+)=(.*)$', raw, re.M))
    uptime = float(re.findall(r'^(\d+\.\d+) \d+\.\d+$', raw, re.M)[0])
    assert re.search(r'^0$', raw, re.M), 'taint is not zero'
    assert 'underrun:       0' in raw and 'frame_done_cnt:0mode:' in raw
    assert '\n1\nsnapshot:count=1\n' in raw
    assert values['POWER_SUPPLY_CAPACITY'] == '99'
    assert values['POWER_SUPPLY_STATUS'] == 'Not charging'
    assert values['POWER_SUPPLY_CURRENT_NOW'] == '0'
    return {'uptime_seconds': uptime, 'taint': 0, 'display_timeouts': 0,
            'display_underruns': 0, 'tracing_on': 1, 'snapshot_remaining_count': 1,
            'power_supply': values}

states = {name: state(name) for name in captures if name.endswith('-state.txt')}
assert 'f02d218a-cc7d-4b92-8858-c8eeaeab5777' in text('short-before-state.txt')
assert '#85 SMP PREEMPT' in text('short-before-state.txt')
assert states['short-before-state.txt']['uptime_seconds'] < states['short-after-state.txt']['uptime_seconds']
assert states['chemistry-before-state.txt']['uptime_seconds'] < states['chemistry-after-state.txt']['uptime_seconds']
assert states['final-state.txt']['uptime_seconds'] > states['chemistry-after-state.txt']['uptime_seconds']
assert text('final-trace-config.txt').splitlines() == [
    '2051', 'nop', 'local global counter uptime perf [mono] mono_raw boot tai', 'X',
]
assert text('short-reader-exit.txt').strip() == '1'
short = text('short-registers.txt')
assert 'identity read: No such device or address' in short
assert 'address=0x58' in short and 'data_writes=0 otp_fault_reads=0' in short
assert not re.search(r'reg=|value=|identity=|threshold=|mode=', short)
assert text('chemistry-reader-exit.txt').strip() == '0'
assert text('chemistry-refusal.txt') == 'Refusing adapter/client/driver mismatch\nreader_exit=2\n'

mp_values = []
for name in ['short-before-mp2650.txt', 'short-after-mp2650.txt', 'chemistry-mp2650.txt']:
    raw = text(name)
    assert 'transactions=12 data_writes=0 fault_reads=0' in raw
    pairs = re.findall(r'^reg=(0x[0-9a-f]{2}) value=(0x[0-9a-f]{2})$', raw, re.M)
    assert len(pairs) == 12 and len(dict(pairs)) == 12
    mp_values.append(dict(pairs))
assert mp_values[0] == mp_values[1] == mp_values[2]
baseline = (Path(__file__).resolve().parent.parent / 'kernel84/final-registers.txt').read_text()
assert mp_values[0] == dict(re.findall(r'^reg=(0x[0-9a-f]{2}) value=(0x[0-9a-f]{2})$', baseline, re.M))
partition_hashes = text('short-partition-hashes.txt').splitlines()
assert partition_hashes == [
    '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405  -',
    '60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b  /dev/sde32',
]
assert text('final-partition-hashes.txt') == text('short-partition-hashes.txt')

query = text('chemistry-query.txt')
assert 'identity legacy_word=0xffa5' in query
assert 'exact_legacy_type_fw_guard=PASS fixed_OEM_queries=004b,0054 retries=0 configuration_data_writes=0' in query
responses = {}
for name, command, size in [('FirmwareVersion', 2, 11), ('stock_chemistry', 0x4b, 4), ('stock_operation_status', 0x54, 4)]:
    line = next(line for line in query.splitlines() if line.startswith(name + ' command='))
    block = bytes.fromhex(re.search(r'response=([0-9a-f]{72})', line)[1])
    assert len(block) == 36 and block[:2] == command.to_bytes(2, 'little')
    assert block[35] == size + 4
    assert block[34] == (255 - sum(block[:block[35] - 2])) & 255
    assert 'validation=0' in line
    payload = block[2:2 + size]
    if size == 4:
        four = re.search(name + r' stock_four_payload_bytes=([0-9a-f]{8})', query)[1]
        assert payload == bytes.fromhex(four)
    responses[name] = {'command': hex(command), 'raw_block': block.hex(), 'payload': payload.hex(),
                       'echo_length_checksum_verified': True, 'OEM_four_byte_read_agrees': size == 4}
assert responses['FirmwareVersion']['payload'] == '2719000400060003850200'
assert responses['stock_chemistry']['payload'] == '4c494f4e'
operation = int.from_bytes(bytes.fromhex(responses['stock_operation_status']['payload']), 'little')
assert operation == 0x386 and operation >> 28 & 1 == 0

temperatures = {}
for name in ['chemistry-before-temperatures.txt', 'chemistry-after-temperatures.txt']:
    rows = []
    for label, selector, raw_bytes, word in re.findall(r'^(\w+) selector=0x([0-9a-f]{2}) bytes=([0-9a-f]{4}) unsigned_word=(\d+)', text(name), re.M):
        value = int(word)
        assert int.from_bytes(bytes.fromhex(raw_bytes), 'little') == value
        row = {'label': label, 'selector': '0x' + selector, 'bytes': raw_bytes, 'word': value}
        if selector in ['06', '28']:
            row['tentative_degrees_C'] = round(value / 10 - 273.15, 2)
        if selector in ['0c', '14']:
            row['signed_mA'] = value if value < 32768 else value - 65536
        rows.append(row)
    assert [row['selector'] for row in rows] == ['0x06', '0x28', '0x08', '0x0c', '0x14']
    temperatures[name] = rows

dmesg_notes = {}
for name in captures:
    if name.endswith('-dmesg.txt'):
        raw = text(name)
        assert '7.3.0-rc6-rmx1931-samurai+' in raw
        assert not re.search(r'(?i)kernel panic|\bBUG:|\bOops:|frame done timeout|frame_done_timeout', raw)
        dmesg_notes[name] = [line for line in raw.splitlines() if re.search(r'(?i)i2c|nack|timeout', line)]
result = {
    'audit': 'PASS', 'kind': 'offline captured observation audit, not protection acceptance',
    'archives': archive_manifest, 'states': states,
    'short_ic': {'address': '0x58', 'identity_attempts': 1, 'identity_read_successes': 0,
                 'result': 'ENXIO', 'threshold_and_mode_queries': 0,
                 'absence_proven': False, 'protection_verified': False},
    'chemistry': 'LION', 'responses': responses,
    'OEM_operation_status_u32': operation, 'OEM_balancing_bit28': 0,
    'exact_2719_protection_threshold_mapping_verified': False,
    'standard_words': temperatures, 'MP2650_fixed_register_values': mp_values[0],
    'MP2650_fixed_reads': 36, 'MP2650_configuration_changes': False,
    'wrong_adapter_refusal_exit': 2, 'partition_hashes': partition_hashes,
    'dmesg_I2C_and_timeout_lines': dmesg_notes,
    'configuration_data_writes': 0, 'wire_includes_register_selectors_and_MAC_request_writes': True,
    'charge_control_verified': False, 'charging_rate_verified': False,
    'temperature_calibration_verified': False,
}
(OUT / 'observations-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: all 26 raw members preserved; 23 device hashes; ENXIO stopped after first identity; LION/0054 blocks verified; MP values unchanged.')
print('Capture state uptimes:', {name: data['uptime_seconds'] for name, data in states.items()})
