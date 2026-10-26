from pathlib import Path
import json, os, subprocess, tarfile, time

os.umask(0o077)
out=Path('/var/lib/samurai/k169-idle');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#168 ')
patterns={'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out',
          'queue_full':'Message buffer unavailable','resume_failed':'NGD resume failed','gpu_fault':'gpu fault:'}
start=time.monotonic();rows=[]
desktop={name:subprocess.check_output(['pgrep','-x',name]).decode().strip() for name in ['phosh','phoc']}
for i in range(21):
    log=subprocess.check_output(['dmesg'],text=True)
    pcm={str(p):p.read_text().strip() for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')}
    amps=''.join(Path('/sys/bus/i2c/devices/'+n+'/status').read_text() for n in ['1-0039','1-003a'])
    row=dict(elapsed=time.monotonic()-start,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
             same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
             fault_counts={n:log.count(p) for n,p in patterns.items()},all_pcm_closed=all(v=='closed' for v in pcm.values()),
             amplifiers_off=amps.count('powered=0 muted=1')==2,
             desktop_same=all(subprocess.check_output(['pgrep','-x',n]).decode().strip()==pid for n,pid in desktop.items()),
             ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip())
    rows.append(row)
    assert row['same_boot'] and row['taint']==0 and all(v==0 for v in row['fault_counts'].values())
    assert row['all_pcm_closed'] and row['amplifiers_off'] and row['desktop_same']
    (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
    if i<20: time.sleep(6)
(out/'dmesg-final-private.txt').write_text(log)
report=dict(stage=169,kernel_build=168,samples=len(rows),seconds=rows[-1]['elapsed'],
            same_boot_and_desktop=True,all_samples_taint0=True,all_pcm_closed=True,amplifiers_off=True,
            faults_final=rows[-1]['fault_counts'],ngd_pm_final=rows[-1]['ngd_pm'],extended_reliability_proven=False)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k169-idle-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
