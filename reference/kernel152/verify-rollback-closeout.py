from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
os.umask(0o077)
out=Path('/var/lib/samurai/k152-rollback147-closeout')
assert not out.exists()
assert os.uname().version.startswith('#147 ')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k152-rollback147-display-recovery/boot-id-private.txt').read_bytes()
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
for name,args in [
    ('partition-check.txt',['sha256sum','-c','/var/lib/samurai/k152-preflash/partition-check.sha256']),
    ('module-check.txt',['sha256sum','-c','/var/lib/samurai/k152-preflash/old132-module-tree.sha256']),
    ('nv-check.txt',['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])]:
    r=subprocess.run(args,cwd='/usr/lib/modules/'+os.uname().release,capture_output=True)
    (out/name).write_bytes(r.stdout+r.stderr)
    r.check_returncode()
installed=Path('/usr/lib/libvulkan_freedreno.so')
assert hashlib.sha256(installed.read_bytes()).hexdigest()=='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
service=Path('/etc/init.d/k152-startup-trace')
assert service.exists()
assert hashlib.sha256(service.read_bytes()).hexdigest()==Path('/var/lib/samurai/k152-tools/service-sha256.txt').read_text().strip()
assert not Path('/sys/kernel/tracing/instances/k152-startup').exists()
r=subprocess.run(['rc-update','del','k152-startup-trace','boot'],capture_output=True,check=True)
(out/'remove-service.txt').write_bytes(r.stdout+r.stderr)
shutil.copy2(service,out/'removed-service')
service.unlink()
Path('/run/k152-startup-trace.pid').unlink(missing_ok=True)
card=Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve(strict=True)
debug=Path('/sys/kernel/debug/dri')/card.name.removeprefix('card')
samples=[]
for i in range(9):
    log=subprocess.check_output(['dmesg'],text=True)
    row=dict(index=i,uptime=float(Path('/proc/uptime').read_text().split()[0]),
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        counts={k:log.count(v) for k,v in dict(dpu_timeouts='frame done timeout',dsi_errors='dsi_err_worker',
            gpu_faults='gpu fault:',warnings='WARNING:',dma_prepare='unable to prepare channel').items()},
        desktop={n:bool(subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True).stdout) for n in ['phoc','phosh']})
    samples.append(row)
    (out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    if i<8:time.sleep(5)
(out/'dmesg-private.txt').write_text(log)
(out/'drm-private.txt').write_text((debug/'state').read_text())
report=dict(stage=152,kernel_build=147,rollback_write_readback_verified=True,boot_and_persist_preserved=True,
    module_tree_preserved=True,nv_sources_preserved=True,mesa149_fix_preserved=True,
    new_boot=True,same_boot_during_closeout=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
    taint=samples[-1]['taint'],desktop_present=all(samples[-1]['desktop'].values()),
    counts_after=samples[-1]['counts'],counts_stable=all(s['counts']==samples[0]['counts'] for s in samples),
    observed_seconds=samples[-1]['uptime']-samples[0]['uptime'],sample_count=len(samples),
    temporary_startup_service_removed=True,physical_desktop_confirmed_by_user=True,
    startup_bug_still_open=True,candidate152_accepted=False)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert report['desktop_present'] and report['taint']==0 and report['counts_stable']
