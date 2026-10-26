from pathlib import Path
import hashlib,json,re,tarfile
import host

p=host.ssh('test -f /var/lib/samurai/k187-a11-trial/trial-exit.txt && sha256sum /tmp/k187-a11-trial.tar')
digest=p.stdout.decode().split()[0]
path=host.PRIVATE/'a11-first-trial-private.tar'
host.download('/tmp/k187-a11-trial.tar',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'a11-first-evidence-private'
with tarfile.open(path) as tar:tar.extractall(folder,filter='data')
read=lambda name:(folder/name).read_text()
assert all(read(name).strip()=='0' for name in ['start-exit.txt','attributes-exit.txt','light-exit.txt','trial-exit.txt','stop-exit.txt'])
assert read('slpi-final-state.txt').strip()=='offline' and read('power-final.txt').strip()=='vdd=0 vddio=0'
assert read('firmware-final.txt').strip()=='qcom/sm8150/realme/samurai/slpi.mdt'
assert read('source-before.txt')==read('source-after.txt') and read('nv-before.txt')==read('nv-after.txt')
attrs=json.loads(read('attributes/summary.json'))
light=json.loads(read('light/summary.json'))
assert attrs['complete'] and attrs['all_requests_acknowledged_once'] and attrs['failed_operations']==0
assert all(attrs['suid_types'][name]==1 for name in ['accel','gyro','mag'])
assert light['success'] and light['disable_ack'] and light['samples']>0
before=read('dmesg-before.txt');after=read('dmesg-final.txt')
assert after.startswith(before)
window=after[len(before):]
faults={key:window.count(value) for key,value in {
    'warning':'WARNING:','oops':'Oops:','scm_assignment':'Assign memory protection call failed',
    'fastrpc_probe':'probe with driver qcom,fastrpc failed','slpi_start_timeout':'2400000.remoteproc: start timed out',
    'asoc':'ASoC error','gpu':'gpu fault:','bluetooth_reassembly':'Frame reassembly failed'}.items()}
assert not any(faults.values())
types=sorted({v for item in attrs['inventory'] for v in item.get('data_type',[]) if isinstance(v,str)})
report=dict(stage=187,kernel_build=183,a11_first_start_exit=0,attribute_census_complete=True,
    wildcard_suid_count=attrs['suid_types'][''],accel_instances=1,gyro_instances=1,mag_instances=1,
    data_types=types,light_sampling=light,original_firmware_pointer_restored=True,
    slpi_final='offline',sensor_supplies_off=True,nv_and_original_sources_unchanged=True,
    fault_delta=faults,evidence_archive_sha256=digest,
    imu_measurements_verified=False,desktop_integration_verified=False,
    a11_default_firmware_deployed=False)
ref=Path(__file__).resolve().parent
(ref/'a11-first-validation.json').write_text(json.dumps(report,indent=2)+'\n')
stats=read('trace-stats-private.txt')
overruns=[int(v) for v in re.findall(r'(?m)^overrun:\s*(\d+)',stats)]
trace=read('scm-glink-trace-private.txt')
scmreq=[line for line in trace.splitlines() if 'scm_smc_request:' in line]
scmdone=[line for line in trace.splitlines() if 'scm_smc_done:' in line]
trace_report=dict(trace_captured=True,per_cpu_overruns=overruns,scm_request_records=len(scmreq),
    scm_done_records=len(scmdone),trace_complete_without_overrun=bool(overruns) and not any(overruns),
    actual_owner_masks_not_available_from_this_trace=True,evidence_archive_sha256=digest)
(ref/'trace-first-validation.json').write_text(json.dumps(trace_report,indent=2)+'\n')
print(json.dumps(report));print(json.dumps(trace_report))
