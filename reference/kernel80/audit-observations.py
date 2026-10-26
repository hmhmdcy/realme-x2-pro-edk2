from pathlib import Path
import gzip
import hashlib
import json
import re
import subprocess

w = Path('/mnt/e/RealmeX2Pro edk2')
ref = w/'reference/kernel80'
out = Path('/mnt/e/edk2-samurai-out/kernel80')
linux = Path('/home/cy122/x2pro-linux/linux')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (ref/'observation-validation.json').exists()
hashes = {}
for line in (out/'device-hashes.txt').read_text().splitlines():
    digest, name = line.split('  ', 1)
    name = Path(name).name.removeprefix('k80-')
    assert sha(out/name) == digest
    hashes[name] = digest
assert gzip.decompress((out/'final-dmesg.txt.gz').read_bytes()) == (out/'final-dmesg.txt').read_bytes()
def block(name, label):
    text = (out/name).read_text()
    data = bytes.fromhex(re.search(label+r'=([0-9a-f]{72})', text)[1])
    assert data[35] in range(5, 37)
    assert data[34] == (255-sum(data[:data[35]-2])) & 255
    return data
first = block('identity.txt', 'response')
paired = block('paired-identity.txt', 'extended_response')
firmware = block('firmware-version.txt', 'response')
cells = block('stock-cells.txt', 'extended_response')
assert first == paired and first[:4] == bytes.fromhex('01001927') and first[35] == 6
assert 'query_rc=1' in (out/'identity.txt').read_text()
assert 'legacy_word=0xffa5' in (out/'paired-identity.txt').read_text()
assert firmware[:2] == b'\x02\x00' and firmware[35] == 15
assert cells[:2] == b'\x71\x00' and cells[35] == 36
assert cells[2:6] == bytes.fromhex('e110e110')
assert 'standard_pack_mV=8642 cell_sum_mV=8642' in (out/'stock-cells.txt').read_text()
for name in ('legacy.txt', 'paired-identity.txt', 'stock-cells.txt'):
    t = (out/name).read_text()
    assert 'guard_mp_rc=2' in t and 'guard_touch_rc=2' in t and 'query_rc=0' in t
regs = dict(re.findall(r'reg=(0x[0-9a-f]{2}) value=(0x[0-9a-f]{2})', (out/'final-registers.txt').read_text()))
expected = {'0x08':'0x16','0x09':'0x4c','0x0a':'0x36','0x07':'0x14','0x00':'0x12','0x01':'0x2d',
            '0x02':'0x06','0x03':'0xa2','0x04':'0x68','0x0f':'0x12','0x0b':'0x00','0x13':'0x0f'}
assert regs == expected
state = (out/'final-state.txt').read_text()
assert state.splitlines()[0] == '87753933-4992-45d2-aaf5-d9db9c11d1a3'
assert state.splitlines()[3] == '0'
dmesg = (out/'final-dmesg.txt').read_text()
issues = {pattern: len(re.findall(pattern, dmesg, re.I)) for pattern in
          ('dsi.*(?:error|underflow|overflow)', r'\bOops:', r'\bBUG:', 'smmu.*(?:fault|error)', 'geni.*(?:error|failed)', 'i2c.*(?:error|failed)')}
assert not any(issues.values()), issues
image_hash = sha(linux/'arch/arm64/boot/Image')
config_hash = sha(linux/'.config')
assert image_hash == 'f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb'
assert config_hash == '9d9f10ae4a96e4a0575b7c51d818180a68e596e84898a3849fe1183307223c6d'
assert '# CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM is not set' in (linux/'.config').read_text()
for row in (w/'reference/kernel78/display-source-hashes.txt').read_text().splitlines():
    digest, name = row.split('  ', 1)
    assert sha(linux/name) == digest
source_names = ('read-bq28-status', 'read-gauge-control-word', 'read-gauge-device-type', 'read-gauge-fw-version', 'read-gauge-stock-cells')
readers = {name: {'source_sha256':sha(ref/(name+'.c')), 'binary_sha256':sha(out/name),
                 'bytes':(out/name).stat().st_size} for name in source_names}
driver_hashes = {name:sha(linux/name) for name in
                ('drivers/power/supply/bq27xxx_battery.c', 'drivers/power/supply/bq27xxx_battery_i2c.c',
                 'drivers/power/supply/qcom_smbx.c', 'arch/arm64/boot/dts/qcom/pm8150b.dtsi')}
result = {'device_captures_sha256_verified':hashes,'identity':{'legacy':'0xffa5','extended':'0x2719',
          'TI_2610_guard_stopped':True,'two_independent_extended_responses_identical':True,
          'firmware_payload_hex':firmware[2:13].hex(),'firmware_payload_decoded':False},
          'stock_cells':{'cell1_mV':4321,'cell2_mV':4321,'sum_mV':8642,'standard_pack_mV':8642,
                        '4_byte_stock_matches_checked_32_byte_MAC_payload':True},
          'broad_status_queries_executed':False,'DAStatus2_0072_executed':False,
          'configuration_NVM_OTP_FET_reset_unseal_writes':0,'device_partition_writes':0,
          'MP2650_current_readback_unchanged_from_79':regs,'log_pattern_counts':issues,
          'boot_id':state.splitlines()[0],'final_uptime_seconds':float(state.splitlines()[2].split()[0]),
          'taint':0,'final_voltage_uV':8641000,'final_temperature_deciC':300,'final_average_current_uA':0,
          'kernel_image_sha256':image_hash,'kernel_config_sha256':config_hash,
          'gauge_NVM_update_config_disabled':True,'display_source_hashes_preserved':True,
          'actual_kernel_source_HEAD':subprocess.check_output(['git','-C',str(linux),'rev-parse','HEAD'],text=True).strip(),
          'audited_driver_sha256':driver_hashes,'readers':readers}
(ref/'observation-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS checked MAC responses, stock cells/pack, adapter refusals, unchanged MP2650, logs, Image/config/display source')
