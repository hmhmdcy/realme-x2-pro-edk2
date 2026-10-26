from pathlib import Path
import json,os,subprocess,time
os.umask(0o077)
assert os.uname().version.startswith('#158 ')
out=Path('/var/lib/samurai/k159-steady');assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(Path('/var/lib/samurai/k159-first-startup')/'boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
def pids():return {n:subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True,text=True).stdout.split() for n in ['phoc','phosh']}
original=pids();assert all(original.values());rows=[];error=None;started=time.monotonic()
try:
    for i in range(21):
        assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
        dmesg=subprocess.check_output(['dmesg'],text=True)
        row=dict(index=i,uptime=float(Path('/proc/uptime').read_text().split()[0]),
            counts={k:dmesg.count(v) for k,v in dict(kms_init_failures='kms hw init failed',dpu_timeouts='frame done timeout',
                dsi_errors='dsi_err_worker',gpu_faults='gpu fault:',warnings='WARNING:',ufs_uic_timeouts='completion timeout',
                dma_prepare='unable to prepare channel').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()),
            pids_preserved=pids()==original)
        rows.append(row);(out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
        assert row['taint']==0 and row['pids_preserved']
        assert not any(v for k,v in row['counts'].items() if k!='dma_prepare'),row
        if i<20:time.sleep(30)
except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
finally:
    result=dict(stage=159,kernel_build=158,same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
        sample_count=len(rows),elapsed_seconds=time.monotonic()-started,error=error,
        critical_counts_zero=bool(rows) and all(not any(v for k,v in r['counts'].items() if k!='dma_prepare') for r in rows),
        pids_preserved=pids()==original,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        first_sample_uptime=rows[0]['uptime'] if rows else None,last_sample_uptime=rows[-1]['uptime'] if rows else None,
        unexpected_reboot_not_seen_in_observation=True if Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot else False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    assert error is None,result
