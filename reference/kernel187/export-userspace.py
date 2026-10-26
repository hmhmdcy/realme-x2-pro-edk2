from pathlib import Path
import hashlib,json,re,tarfile,shutil
import host

p=host.ssh('test -f /var/lib/samurai/k187-a11-userspace/trial-exit.txt && gzip -c /tmp/k187-a11-userspace.tar > /tmp/k187-a11-userspace-evidence-private.tar.gz && sha256sum /tmp/k187-a11-userspace-evidence-private.tar.gz')
digest=p.stdout.decode().split()[0]
partial=host.PRIVATE/'a11-userspace-private.tar'
if partial.exists():
    saved=host.PRIVATE/'a11-userspace-initial-download-partial-private.tar'
    assert not saved.exists()
    shutil.copyfile(partial,saved)
path=host.PRIVATE/'a11-userspace-evidence-private.tar.gz';host.download('/tmp/k187-a11-userspace-evidence-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'a11-userspace-evidence-private'
with tarfile.open(path) as tar:tar.extractall(folder,filter='data')
read=lambda name:(folder/name).read_text()
assert all(read(name).strip()=='0' for name in ['trial-exit.txt','start-exit.txt','userspace-exit.txt','stop-exit.txt'])
assert read('slpi-final-state.txt').strip()=='offline' and read('power-final.txt').strip()=='vdd=0 vddio=0'
assert read('firmware-final.txt').strip()=='qcom/sm8150/realme/samurai/slpi.mdt'
assert read('source-before.txt')==read('source-after.txt') and read('nv-before.txt')==read('nv-after.txt')
users=json.loads(read('userspace/summary.json'))
assert users['proxy_exit']==0 and users['three_claims_succeeded'] and users['system_library_unchanged'] and users['package_database_unchanged']
assert all(r['samples']>=100 and r['success'] and r['malformed_frames']==0 and r['disable_ack'] for r in users['vectors'].values())
assert all(r['exit']==0 and r['samples']>0 and r['disabled'] for r in users['cli'].values())
before=read('dmesg-before.txt');after=read('dmesg-final.txt');assert after.startswith(before)
extra=after[len(before):]
faults={key:extra.count(value) for key,value in {'warning':'WARNING:','oops':'Oops:',
    'scm_assignment':'Assign memory protection call failed','fastrpc_probe':'probe with driver qcom,fastrpc failed',
    'slpi_start':'2400000.remoteproc: start timed out','slpi_stop':'2400000.remoteproc: timed out on wait',
    'asoc':'ASoC error','gpu':'gpu fault:','bluetooth_reassembly':'Frame reassembly failed'}.items()}
assert not any(faults.values())
summary=dict(stage=187,kernel_build=183,a11_userspace_trial_passed=True,vectors=users['vectors'],
    standard_cli=users['cli'],sensor_proxy=users['sensor_proxy'],three_claims_and_releases_passed=True,
    proxy_exit=0,default_system_library_unchanged=True,package_database_unchanged=True,
    firmware_pointer_restored=True,sensor_supplies_off=True,slpi_offline=True,
    original_sources_and_nv_preserved=True,fault_delta=faults,evidence_archive_sha256=digest,
    dynamic_motion_axes_and_absolute_accuracy_verified=False,persistent_boot_service_deployed=False)
ref=Path(__file__).resolve().parent
(ref/'a11-userspace-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
# Aggregate physical vectors instead of exposing sensor identifiers or calibration.
acc=json.loads(read('userspace/accel/samples-private.json'))
means=[sum(item['values'][i] for item in acc)/len(acc) for i in range(3)]
(host.PRIVATE/'accel-axis-means-private.json').write_text(json.dumps(means)+'\n')
print(json.dumps(summary));print(json.dumps({'accel_mean_axes_for_orientation_analysis':means}))
