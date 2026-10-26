from pathlib import Path
import json, os, re, subprocess, tarfile

os.umask(0o077)
out=Path('/var/lib/samurai/k169-final');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k168-second-runtime/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#168 ')
def capture(name,args):
    p=subprocess.run(args,shell=isinstance(args,str),capture_output=True)
    (out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,(name,p.returncode)
    return p.stdout.decode(errors='replace')
capture('kernel',['uname','-a'])
log=capture('dmesg',['dmesg'])
hashes=dict((line.split()[1],line.split()[0]) for line in capture('partition-hashes',['sha256sum','/dev/sde11','/dev/sde32','/dev/sda2']).splitlines())
capture('nv-check',['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
capture('module-check','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k169-preflash/old132-module-tree.sha256')
capture('amps',['cat','/sys/bus/i2c/devices/1-0039/status','/sys/bus/i2c/devices/1-003a/status'])
desktop=capture('desktop','pgrep -x phosh; pgrep -x phoc')
patterns={'warnings':'WARNING:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out',
          'queue_full':'Message buffer unavailable','resume_failed':'NGD resume failed','gpu_fault':'gpu fault:'}
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
report=dict(stage=169,kernel_build=168,kernel_version=os.uname().version,
            same_boot_as_accepted_second=True,partition_hashes=hashes,persist_and_nv_checked=True,
            modules132_checked=True,desktop_process_count=len(desktop.strip().splitlines()),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),faults={n:log.count(p) for n,p in patterns.items()},
            ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
            uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k169-final-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
