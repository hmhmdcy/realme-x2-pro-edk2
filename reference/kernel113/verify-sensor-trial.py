from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'sensor-ram-v5.tar'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='e125d1e49182a10367f2e831c49a9e02413e710e333e4cf8a187ab41cb13564d'
with tarfile.open(path) as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['power-before.txt'].strip()==data['power-final.txt'].strip()==b'vdd=0 vddio=0'
assert data['power-enabled.txt'].strip()==b'vdd=1 vddio=1'
assert data['power-off-exit.txt'].strip()==b'0' and data['slpi-final-state.txt'].strip()==b'offline'
assert data['start-exit.txt'].strip()==b'0'
assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
for name,count in [('nv-before.txt',6),('nv-after.txt',6),('source-before.txt',4),('source-after.txt',4),('module-check.txt',2)]:
    assert data[name].count(b': OK')==count
log=data['dmesg-final.txt'].decode(errors='replace')
rpc=data['rpcd.txt'].decode(errors='replace')
query=data['accelerometer.txt'].decode(errors='replace')
fatals=re.findall(r'(sns_[a-z_]+\.c:\d+[^\r\n]*)',log)
# Fatal source/condition is diagnostic, without firmware/calibration contents.
fatals=[re.sub(r'\b0x[0-9a-fA-F]{8,}\b','<address>',s) for s in fatals]
report=dict(trial_audit_pass=True,kernel_build=113,archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            manual_supply_enable_and_disable=True,slpi_started=True,slpi_final='offline',taint=0,
            power_refs_final_off=True,nv6_sources4_unchanged=True,
            query_exit=int(data['query-exit.txt']),daemon_exit=int(data['daemon-exit.txt']),
            dpu_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),
            sensor_i2c_fatal='I2C_ERROR_TRANSFER_TIMEOUT' in log,fatal_conditions=fatals,
            large_input_limit_hit='Large (>256B)' in rpc,large_inputs_completed=rpc.count('large-input('),
            ram_files_opened=rpc.count('ram-open('),ram_writes=rpc.count('ram-write('),
            accel_unavailable="No 'accel' sensor available" in query,
            sensor_function_accepted=False,goal_complete=False)
(out/'sensor-ram-v5-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(ref/'sensor-ram-v5-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
