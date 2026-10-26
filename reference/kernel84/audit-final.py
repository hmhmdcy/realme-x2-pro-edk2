"""Validate final partition, MP2650 and bounded idle-monitor observations."""
from pathlib import Path
import hashlib, json, re, tarfile, gzip

out = Path('/mnt/e/edk2-samurai-out/kernel84')
sha = lambda data: hashlib.sha256(data).hexdigest()
compressed = (out / 'final-raw.tar.gz').read_bytes()
assert sha(compressed) == '4007d22d2a82e41317e44d300cd43e67e993813c327f192d79b309c5012b8e2e'
assert sha(gzip.decompress(compressed)) == 'a3375c604691d0d9c7957029b2cb5839d5a875514d4e37c56ab9c2aa7e0d7873'
raw = {}
with tarfile.open(out / 'final-raw.tar.gz') as tar:
    for member in tar:
        assert member.isfile() and member.name.startswith('tmp/k84-final-')
        assert '/' not in member.name.removeprefix('tmp/')
        name = member.name.removeprefix('tmp/k84-')
        data = tar.extractfile(member).read()
        target = out / name
        if target.exists():
            assert target.read_bytes() == data
        else:
            target.write_bytes(data)
        raw[name] = data
for line in raw['final-hashes.txt'].decode().splitlines():
    digest, path = line.split('  ', 1)
    assert sha(raw[Path(path).name.removeprefix('k84-')]) == digest
state = raw['final-state.txt'].decode()
assert state.startswith('f02d218a-cc7d-4b92-8858-c8eeaeab5777\n')
assert '#85 SMP PREEMPT' in state and state.splitlines()[3] == '0'
assert 'frame_done_cnt:0mode:' in state and re.search(r'underrun:\s+0\s', state)
read_registers = lambda b: dict(re.findall(r'^reg=(0x[0-9a-f]+) value=(0x[0-9a-f]+)$', b.decode(), re.M))
assert read_registers(raw['final-registers.txt']) == read_registers((out / 'before-registers.txt').read_bytes())
assert len(read_registers(raw['final-registers.txt'])) == 12
assert 'transactions=12 data_writes=0 fault_reads=0' in raw['final-registers.txt'].decode()
monitor = raw['final-monitor-settings.txt'].decode().splitlines()
assert monitor[0] == 'nop' and '[mono]' in monitor[1]
assert monitor[2:5] == ['2051', '1', 'snapshot:count=1']
assert not re.search(r'trace_boot: Failed|frame done timeout|dsi_err_worker|\bBUG:|\bOops:', raw['final-dmesg.txt'].decode())
partitions = raw['final-partition-hashes.txt'].decode()
assert '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405  -' in partitions
assert '60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b  /dev/sde32' in partitions

def config(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            name, value = line.split('=', 1)
            values[name] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values

old, first, ready = [config(out / name) for name in ['config-before', 'config-trace', 'config-ready']]
delta = lambda a, b: {name: {'before': a.get(name), 'after': b.get(name)} for name in sorted(a.keys() | b.keys()) if a.get(name) != b.get(name)}
report = {
    'archive_sha256': sha(gzip.decompress(compressed)),
    'compressed_archive_sha256': sha(compressed), 'members_and_sha256_verified': True,
    'boot_id': state.splitlines()[0], 'kernel_build': 85,
    'uptime_seconds': float(state.splitlines()[2].split()[0]), 'taint': 0,
    'boot_prefix_unchanged': True, 'logdump_verified': True,
    'timeout_count': 0, 'underrun_count': 0,
    'mp2650_fixed_reads': 12, 'mp2650_registers_match_predeployment': True,
    'mp2650_configuration_data_written': False,
    'i2c_register_selector_write_messages_performed': True,
    'gauge_charger_protection_control_accepted': False,
    'battery_voltage_uv': int(re.search(r'POWER_SUPPLY_VOLTAGE_NOW=(\d+)', state)[1]),
    'battery_capacity_percent': int(re.search(r'POWER_SUPPLY_CAPACITY=(\d+)', state)[1]),
    'battery_temp_tenths_c': int(re.search(r'POWER_SUPPLY_TEMP=(\d+)', state)[1]),
    'display_trace_monitor_armed': True, 'snapshot_action_remaining': 1,
    'runtime_buffer_actual_kib_per_cpu': 2051, 'boot_buffer_actual_kib_per_cpu': 513,
    'runtime_resize_persists_across_reboot': False,
    'first_iteration_config_delta': delta(old, first),
    'correction_config_delta': delta(first, ready),
    'new_optical_observation': False, 'display_root_cause_fixed': False,
}
(out / 'final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS final hashes/partitions; MP2650 12 values unchanged; taint0, timeout0, monitor armed.')
print('First iteration configuration changes:', len(report['first_iteration_config_delta']))
print('Correction configuration changes:', json.dumps(report['correction_config_delta']))
