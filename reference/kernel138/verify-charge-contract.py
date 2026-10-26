from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel138'
out = Path('/mnt/e/edk2-samurai-out/kernel138')
def load(path):
    with tarfile.open(path) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    assert len(data['SHA256SUMS'].splitlines()) == len(data) - 1
    return data
d = load(out / 'charge-contract-private.tar.gz')
health = load(out.parent / 'kernel137/rollback132-health-private.tar.gz')
assert d['boot-id-private.txt'] == health['boot-id-private.txt']
restore = json.loads(d['binding-restoration.json'])
assert restore['same_of_client_rebound'] and restore['charger_configuration_data_writes'] == 0
assert not restore['forced_address_ownership']
assert not restore['new_device_or_delete_device_used']
assert d['final-taint.txt'].strip() == b'0'
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1), ('package-db-final-check.txt', 2)]:
    assert d[name].count(b': OK') == count and b'FAILED' not in d[name]
for name in ['phosh', 'phoc']:
    assert d[name + '-before.txt'].strip() and d[name + '-before.txt'] == d[name + '-after.txt']
registers = []
for name in ['registers-first.txt', 'registers-second.txt']:
    text = d[name].decode()
    assert 'transactions=12 data_writes=0 fault_reads=0' in text
    registers.append({int(a,16):int(b,16) for a,b in re.findall(r'reg=0x([0-9a-f]+) value=0x([0-9a-f]+)',text)})
assert len(registers[0]) == 12 and registers[0] == registers[1]
v = registers[0]
assert v[0] == v[0xf] == 0x12 and v[7] >> 6 == 0
old = json.loads((r / 'reference/kernel133/charge-control-contract-validation.json').read_text())
assert {f'0x{k:02x}':f'0x{x:02x}' for k,x in v.items()} == old['registers']
stock_meta = json.loads((r / 'reference/kernel76/stock-source-manifest.json').read_text())
for name in ['oppo_mp2650.c', 'oppo_mp2650.h']:
    expected = stock_meta['files']['drivers/power/oppo/charger_ic/' + name]['sha256']
    assert hashlib.sha256((out.parent / 'kernel76' / ('stock-' + name)).read_bytes()).hexdigest() == expected
policy = json.loads((r / 'reference/kernel76/charging-stock-runtime-facts.json').read_text())['live_policy']
assert next(item['u32'] for name,item in policy.items() if name.endswith('/qcom,vbatt_num')) == [2]
cells = 2
voltage_code = (v[4] & 0x7e) >> 1
cell_target_uv = 3712500 + voltage_code * 12500
cell_recharge_drop_uv = 100000 * (1 + (v[4] & 1))
pack_target_uv = cells * cell_target_uv
pack_recharge_threshold_uv = cells * (cell_target_uv - cell_recharge_drop_uv)
def gauge(name):
    values = dict(line.split('=',1) for line in d[name].decode().splitlines() if line.startswith('POWER_SUPPLY_'))
    return {key.removeprefix('POWER_SUPPLY_').lower():values[key] for key in [
        'POWER_SUPPLY_STATUS','POWER_SUPPLY_CAPACITY','POWER_SUPPLY_TEMP',
        'POWER_SUPPLY_VOLTAGE_NOW','POWER_SUPPLY_CURRENT_NOW','POWER_SUPPLY_HEALTH']}
gauges = [gauge(name) for name in ['gauge-before-private.txt','gauge-after-private.txt']]
assert all(int(g['voltage_now']) > pack_recharge_threshold_uv for g in gauges)
assert (v[0x13] & 0xc) >> 2 == 3
counts = {}
for name,pattern in [('gpu_faults','gpu fault:'),('dpu_timeouts','frame done timeout'),
                     ('dsi_errors','dsi_err_worker'),('warnings','WARNING:')]:
    before = d['dmesg-before-private.txt'].decode().count(pattern)
    after = d['dmesg-after-private.txt'].decode().count(pattern)
    assert before == after
    counts[name] = dict(before=before,after=after)
report = dict(stage=138,current_kernel=132,same_rollback132_boot_verified=True,
    archive_sha256=hashlib.sha256((out/'charge-contract-private.tar.gz').read_bytes()).hexdigest(),
    two_config_snapshots_identical=True,config_unchanged_since133=True,
    register04=f'0x{v[4]:02x}',register13=f'0x{v[0x13]:02x}',
    cell_count_from_oem_dt_and_config=2,voltage_code=voltage_code,
    programmed_cell_target_uv=cell_target_uv,programmed_pack_target_uv=pack_target_uv,
    programmed_cell_recharge_drop_uv=cell_recharge_drop_uv,
    programmed_pack_recharge_threshold_uv=pack_recharge_threshold_uv,
    readings=gauges,charger_state='charge termination',
    above_hardware_recharge_threshold=True,
    hardware_full_latch_consistent_with_readings=True,
    positive_charge_current_or_recharge_cycle_accepted=False,
    inherited_settings_are_not_recommended_limits=True,
    nominal_input_limit_ma=900,negotiated_source_budget_available=False,
    protection_chain_and_fail_closed_control_verified=False,
    configuration_data_writes=0,fault_register_reads=0,existing_observation_driver_rebound=True,
    unbound_seconds=restore['unbound_seconds'],desktop_pids_unchanged=True,
    source_vendor_package_hashes_passed=True,taint=0,counts=counts,
    charging_control_accepted=False,goal_complete=False)
(ref/'charge-threshold-validation.json').write_text(json.dumps(report,indent=2)+'\n')
health_report = json.loads(health['health-validation.json'])
(r/'reference/kernel137/rollback-health-validation.json').write_text(json.dumps(health_report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
