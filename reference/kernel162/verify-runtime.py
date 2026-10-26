"""Verify new kernel identity, intended partition and preserved GPU repair."""
from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077)
out=Path('/var/lib/samurai/k162-first-runtime')
assert not out.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#158 ')
assert boot!=Path('/var/lib/samurai/k162-preflash/boot-id-private.txt').read_bytes()
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
expected=json.loads(Path('/var/lib/samurai/k162-tools/build-package-validation.json').read_text())
original=dict(line.split()[::-1] for line in Path('/var/lib/samurai/k162-preflash/partition-check.sha256').read_text().splitlines())
hashes={}
for path in ['/dev/sde11','/dev/sde32','/dev/sda2']:
    hashes[path]=subprocess.check_output(['sha256sum',path],text=True).split()[0]
(out/'partition-hashes-private.json').write_text(json.dumps(hashes,indent=2))
assert hashes['/dev/sde11']==original['/dev/sde11']
assert hashes['/dev/sda2']==original['/dev/sda2']
assert hashes['/dev/sde32']==expected['logdump_sha256']
library=hashlib.sha256(Path('/usr/lib/libvulkan_freedreno.so').read_bytes()).hexdigest()
assert library=='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
for name,args in [
    ('module-check.txt',['sha256sum','-c','/var/lib/samurai/k162-preflash/old132-module-tree.sha256']),
    ('nv-check.txt',['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])]:
    r=subprocess.run(args,cwd='/usr/lib/modules/'+os.uname().release,capture_output=True)
    (out/name).write_bytes(r.stdout+r.stderr)
    r.check_returncode()
rows=[]
for i in range(10):
    log=subprocess.check_output(['dmesg'],text=True)
    rows.append(dict(index=i,uptime=float(Path('/proc/uptime').read_text().split()[0]),
        counts={k:log.count(v) for k,v in dict(kms_init_failures='kms hw init failed',dpu_timeouts='frame done timeout',dsi_errors='dsi_err_worker',
        gpu_faults='gpu fault:',warnings='WARNING:',dma_prepare='unable to prepare channel').items()},
        desktop={n:bool(subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True).stdout) for n in ['phoc','phosh']},
        taint=int(Path('/proc/sys/kernel/tainted').read_text())))
    (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
    if i<9:time.sleep(3)
(out/'dmesg-private.txt').write_text(log)
report=dict(stage=162,kernel_build=158,new_boot=True,logdump_readback_exact=True,
    boot_and_persist_preserved=True,modules132_verified=True,mesa149_fix_preserved=True,
    library_sha256=library,elapsed_sample_seconds=rows[-1]['uptime']-rows[0]['uptime'],
    samples=rows,counts_after=rows[-1]['counts'],taint=rows[-1]['taint'],
    desktop_present=all(rows[-1]['desktop'].values()),
    counts_stable=all(x['counts']==rows[0]['counts'] for x in rows),
    preservation_reference_from_current158_before_same_image_reboot=True,hardware_display_root_cause_confirmed=False)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert report['desktop_present'] and report['taint']==0
assert not any(report['counts_after'][key] for key in ['kms_init_failures','dpu_timeouts','dsi_errors','gpu_faults','warnings']),report['counts_after']
