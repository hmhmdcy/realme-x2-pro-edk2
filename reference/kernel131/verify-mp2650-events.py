import hashlib
import json
from pathlib import Path
import re
import tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel131')
path = private / 'k131-mp2650-events-r2-private.tar.gz'
assert hashlib.sha256(path.read_bytes()).hexdigest() == Path(str(path) + '.sha256').read_text().split()[0]
with tarfile.open(path) as archive:
    files = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
manifest = files['SHA256SUMS'].decode().splitlines()
assert len(manifest) == len(files) - 1
for entry in manifest:
    expected, name = entry.split('  ', 1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest() == expected
samples = json.loads(files['samples-private.json'])
assert len(samples) == 8
assert files['final-taint.txt'].strip() == b'0'
assert files['client-final-absent.txt'].strip() == b'true'
permissions = json.loads(files['permissions.json'])
assert all(mode & 0o222 == 0 for mode in permissions.values())
values = {}
for prop in ['online', 'status', 'voltage_now', 'current_now']:
    readings = [sample['properties'][prop] for sample in samples]
    values[prop] = {'valid_samples': sum('value' in item for item in readings),
                    'unavailable_errno': [item['errno'] for item in readings if 'errno' in item]}
    valid = [item['value'].strip() for item in readings if 'value' in item]
    values[prop]['values' if prop in ['online', 'status'] else 'range'] = sorted(set(valid)) if prop in ['online', 'status'] else [min(map(int, valid)), max(map(int, valid))] if valid else []
events = []
for sample in samples:
    event = sample['properties']['uevent']
    assert 'value' in event and event['value'].strip()
    event = dict(line.split('=', 1) for line in event['value'].splitlines())
    assert event['POWER_SUPPLY_NAME'] == 'mp2650-input'
    assert event['POWER_SUPPLY_TYPE'] == 'USB'
    assert 'POWER_SUPPLY_ONLINE' in event and 'POWER_SUPPLY_STATUS' in event
    events.append(event)
regs = []
for name in ['registers-before.txt', 'registers-after.txt']:
    regs.append(dict(re.findall(r'reg=(0x[0-9a-f]+) value=(0x[0-9a-f]+)', files[name].decode())))
assert len(regs[0]) == len(regs[1]) == 12
assert {k: v for k, v in regs[0].items() if k != '0x13'} == {k: v for k, v in regs[1].items() if k != '0x13'}
before = files['dmesg-before.txt'].decode().splitlines()
after = files['dmesg-after.txt'].decode().splitlines()
assert after[:len(before)] == before
assert not any(re.search(r'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT|frame_done.*timed out|RCU.*stall', line, re.I) for line in after[len(before):])
assert all(line.endswith(': OK') for line in files['package-db-final-check.txt'].decode().splitlines())
assert 'address ownership' in files['busy-reader-refusal.txt'].decode()
result = dict(kernel=129, archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              verified_members=len(manifest), samples=8, nonempty_standard_uevents=8,
              online_status_present_in_all_events=True, properties=values,
              eleven_configuration_registers_unchanged=True, address_busy_refused=True,
              attributes_read_only=True, temporary_client_removed=True,
              package_db_preserved=True, new_gpu_faults_during_this_test=0,
              full_charging_control_accepted=False, adc_external_calibration=False,
              persistent_binding=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel131/mp2650-event-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
