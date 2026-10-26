from pathlib import Path
import hashlib,json,tarfile,re
out=Path('/mnt/e/edk2-samurai-out/kernel119');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
    with tarfile.open(path) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
    for line in d['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
    return d
source=load(out/'benchmark-source-private.tar.gz')
test=load(out/'pixel-validation-private.tar.gz')
post=load(out/'post-pixel-fault-private.tar.gz')
assert sha(out/'post-pixel-fault-private.tar.gz')=='1b1aaa5138818d3499966352fe826f934268d45e2b8b8aedfb59906c1d9620f5'
identity=(out/'current-boot-id-private.txt').read_bytes()
for d in [source,test,post]:assert d['boot-id-private.txt']==identity
assert b': OK' in source['signature-final-verify.txt']
for d,name in [(source,'package-db-final-check.txt'),(test,'package-db-final-check.txt'),(post,'package-db-check.txt')]:assert d[name].count(b': OK')==2 and b'FAILED' not in d[name]
log=test['validation.txt'].decode();assert 'GL_VENDOR:      freedreno' in log and 'GL_RENDERER:    FD640' in log
results=re.findall(r'Validation: (Success|Failure|Unknown)',log)
assert len(results)==33 and results.count('Success')==2 and results.count('Failure')==25 and results.count('Unknown')==6
assert test['validation-exit.txt'].strip()==b'0' and not test['remaining-processes.txt'].strip()
assert post['state.txt'].splitlines()[-1]==b'0' and post['phosh.txt'].strip() and post['phoc.txt'].strip()
assert post['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0' and post['radio-audio.txt'].strip()==b'running\nrunning'
assert post['pcm.txt'].strip()==b'closed\nclosed' and post['amps.txt'].count(b'powered=0 muted=1')==2
assert post['traces.txt'].strip()==b'0\n0'
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert post[name].count(b': OK')==count and b'FAILED' not in post[name]
before=test['dmesg-before.txt'].decode();immediate=test['dmesg-after.txt'].decode();later=post['dmesg.txt'].decode()
exit_uptime=float(test['uptime-after.txt'].split()[0])
fault_times=[float(t) for t in re.findall(r'^\[\s*([0-9.]+)\].*\*\*\* gpu fault',later,re.M)]
assert len(fault_times)==1 and fault_times[0]>exit_uptime
cores={name:body for name,body in post.items() if name.endswith('-private.data')}
core_dir=out/'gpu-coredump';core_dir.mkdir(mode=0o700,exist_ok=True)
for name,body in cores.items():(core_dir/Path(name).name).write_bytes(body)
meta=[]
for name,body in cores.items():
    text=body.decode(errors='replace')
    # Keep complete dumps private; publish only the diagnostic owner category.
    owner='glmark2' if re.search(r'^comm: glmark2[^\n]*$',text[:10000],re.M) else ('phoc' if re.search(r'^comm: phoc\s*$',text[:10000],re.M) else 'unknown')
    meta.append(dict(file=Path(name).name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),owner_category=owner))
report=dict(kernel_build=118,nonroot_signed_offscreen_test=True,no_package_install=True,package_database_unchanged=True,renderer='FD640',mesa='26.2.4',es='3.2',validation_cases=33,successes=2,failures=25,unknown=6,exit_zero_does_not_mean_pass=True,tool_processes_released=True,graphics_acceptance=False,immediate_gpu_faults=immediate.count('*** gpu fault'),later_gpu_faults=later.count('*** gpu fault'),new_gpu_faults=later.count('*** gpu fault')-before.count('*** gpu fault'),ccu_read_translation_fault='source=CCU' in later and 'dir=READ type=TRANSLATION' in later,delayed_fault_after_test_exit=True,dpu_timeouts=later.count('frame done timeout'),taint_after=0,phosh_phoc_still_running=True,pcm_closed_amps_idle=True,nv6_source4_vendor_preserved=True,traces_off=True,no_manual_gpu_reset=True,devcoredumps=meta,source_archive_sha256=sha(out/'benchmark-source-private.tar.gz'),test_archive_sha256=sha(out/'pixel-validation-private.tar.gz'),post_fault_archive_sha256=sha(out/'post-pixel-fault-private.tar.gz'),goal_complete=False)
for folder in [out,ref]:(folder/'pixel-result-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
