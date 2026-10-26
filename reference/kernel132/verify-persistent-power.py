from pathlib import Path
import hashlib
import json
import re
import tarfile
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
archive = out / 'persistent-power-private.tar.gz'
with tarfile.open(archive) as tf:
    d = {}
    for m in tf:
        assert (m.isdir() or m.isfile()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
        if m.isfile():
            name = m.name.removeprefix('./')
            assert name not in d
            d[name] = tf.extractfile(m).read()
for line in d['SHA256SUMS'].decode().splitlines():
    h, name = line.split('  ', 1)
    assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest() == h
assert d['boot-id-private.txt'].strip() == (out / 'embedded-boot-id-private.txt').read_bytes().strip()
samples = json.loads(d['samples-private.json'])
assert len(samples) == 8
properties = {}
for prop in ['online', 'status', 'voltage_now', 'current_now']:
    values = [s['properties'][prop]['value'].strip() for s in samples if 'value' in s['properties'][prop]]
    errors = [s['properties'][prop]['errno'] for s in samples if 'errno' in s['properties'][prop]]
    assert all(e == 61 for e in errors)
    properties[prop] = dict(valid_samples=len(values), unavailable_errno=errors)
    if prop in ['voltage_now', 'current_now'] and values:
        numbers = list(map(int, values))
        properties[prop]['range'] = [min(numbers), max(numbers)]
    else:
        properties[prop]['values'] = sorted(set(values))
assert properties['online']['valid_samples'] == 8 and properties['online']['values'] == ['1']
assert properties['status']['valid_samples'] == 8
events = [s['properties']['uevent']['value'] for s in samples]
assert all('POWER_SUPPLY_ONLINE=1\n' in e and 'POWER_SUPPLY_STATUS=' in e and e.strip() for e in events)
assert all(m == 0o444 for m in json.loads(d['permissions.json']).values())
assert d['phosh-before.txt'] == d['phosh-after.txt'] and d['phoc-before.txt'] == d['phoc-after.txt']
assert d['final-taint.txt'].strip() == b'0' and b'started' in d['bluez-service.txt']
for name, count in [('package-db-final-check.txt', 2), ('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1)]:
    assert d[name].count(b': OK') == count and b'FAILED' not in d[name]
before = d['dmesg-before-private.txt'].decode().splitlines()
after = d['dmesg-after-private.txt'].decode().splitlines()
assert after[:len(before)] == before
faults = ['Frame reassembly failed', 'QCA Failed', 'tx timeout', 'firmware crashed', 'frame done timeout', '*** gpu fault', 'Unhandled context fault', 'WARNING:', 'BUG:', 'Oops:']
new = '\n'.join(after[len(before):])
counts = {f: new.count(f) for f in faults}
assert all(v == 0 for v in counts.values())
wifi = d['wifi-link-private.txt'].decode()
match = re.search(r'freq: (\d+)', wifi)
report = dict(kernel=132, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              verified_members=len(d) - 1, samples=8, observation_seconds=samples[-1]['elapsed_seconds'],
              persistent_device_tree_binding=True, auto_registered_after_actual_flash_boot=True,
              standard_nonempty_uevents=8, properties=properties, attributes_read_only=True,
              desktop_pids_unchanged=True, taint=0, new_fault_counts=counts,
              total_boot_gpu_faults=sum(l.count('*** gpu fault') for l in after),
              total_boot_dpu_timeouts=sum(l.count('frame done timeout') for l in after),
              total_boot_uart_reassembly_errors=sum(l.count('Frame reassembly failed') for l in after),
              bluez_service_started=True, wifi_frequency=int(match[1]) if match else None,
              package_db_nv6_source4_vendor1_preserved=True,
              driver_configuration_writes_added=False, full_charging_control_accepted=False,
              adc_external_calibration=False, gpu_overall_acceptance=False, goal_complete=False)
(ref / 'persistent-power-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
