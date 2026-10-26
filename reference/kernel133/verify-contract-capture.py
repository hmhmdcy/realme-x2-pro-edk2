from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
archive = Path('/mnt/e/edk2-samurai-out/kernel133/k133-charge-contract-private.tar.gz')
with tarfile.open(archive, 'r:gz') as tf:
    data = {m.name.removeprefix('./'): tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
verified = 0
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ./', 1)
    assert hashlib.sha256(data[name]).hexdigest() == digest
    verified += 1
assert verified == len(data) - 1
restore = json.loads(data['binding-restoration.json'])
resume = json.loads(data['resume-validation.json'])
assert restore['same_of_client_rebound'] and restore['charger_configuration_data_writes'] == 0
assert resume['resume_read_only'] and resume['i2c_transactions_replayed'] == 0
assert data['final-taint.txt'].strip() == b'0'
for name, count in [('nv-check.txt', 6), ('source-check-r2.txt', 4), ('vendor-check.txt', 1),
                    ('package-db-final-check.txt', 2), ('package-db-resume-check.txt', 2)]:
    lines = data[name].decode().splitlines()
    assert len(lines) == count and all(line.endswith(': OK') for line in lines)
for name in ['phosh', 'phoc']:
    assert data[name + '-before.txt'] == data[name + '-after.txt']
registers = []
for name in ['registers-first.txt', 'registers-second.txt']:
    text = data[name].decode()
    assert 'transactions=12 data_writes=0 fault_reads=0' in text
    values = {int(a, 16): int(b, 16) for a, b in re.findall(r'reg=0x([0-9a-f]+) value=0x([0-9a-f]+)', text)}
    assert len(values) == 12 and 0x14 not in values
    registers.append(values)
assert registers[0] == registers[1]
v = registers[0]
assert v[0] == v[0x0f] == 0x12 and v[7] >> 6 == 0
usb = json.loads(data['usb-descriptor-state.json'])
assert usb['state'] == 'configured' and usb['typec_class_entries'] == 0
before = data['dmesg-before-private.txt'].decode()
after = data['dmesg-after-private.txt'].decode()
counts = {}
for name, pattern in [('gpu_fault', r'gpu fault'), ('dpu_timeout', r'frame_done.*timeout'),
                      ('bt_reassembly', r'reassembl')]:
    a, b = len(re.findall(pattern, before, re.I)), len(re.findall(pattern, after, re.I))
    assert b == a
    counts[name] = dict(before=a, after=b)
report = dict(stage=133, current_kernel=132, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    verified_members=verified, usb_descriptor_state=usb, registers={f'0x{k:02x}': f'0x{x:02x}' for k, x in v.items()},
    two_read_snapshots_identical=True, input_limit_pair_nominal_ma=900,
    descriptor_max_power_ma=100, negotiated_source_budget_available=False,
    descriptor_is_not_measurement_of_source_budget=True, cell_count_encoding=2,
    observation_only_driver_rebound=True, unbound_seconds=restore['unbound_seconds'],
    resume=resume, fault_counts=counts, nv_source_vendor_checks_pass=True,
    charging_control_accepted=False, gpu_overall_acceptance=False, goal_complete=False)
(r / 'reference/kernel133/charge-control-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K133_CAPTURE_HASHES_AND_READONLY_RESUME_VERIFIED', flush=True)
