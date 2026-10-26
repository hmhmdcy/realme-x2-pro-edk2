from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile, sys

os.umask(0o077)
label=sys.argv[1] if len(sys.argv)>1 else 'first'
assert re.fullmatch('[a-z0-9-]+',label)
out=Path('/var/lib/samurai/k166-'+label+'-runtime');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
version=os.uname().version
def capture(name,args):
    p=subprocess.run(args,shell=isinstance(args,str),capture_output=True)
    (out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
    return p.stdout.decode(errors='replace')
log=capture('dmesg',['dmesg'])
capture('audio-state','cat /proc/asound/cards /proc/asound/pcm; for p in /proc/asound/card*/pcm*/sub*/status; do cat "$p"; done; cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status; for p in /sys/bus/platform/devices/qcom,slim-ngd.1/power/*; do echo "$p"; cat "$p" 2>/dev/null; done')
capture('routes','amixer -c 0 contents; su -s /bin/sh cy122 -c "XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks; XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources"')
capture('remoteproc','for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done')
desktop=capture('desktop','pgrep -x phosh; pgrep -x phoc')
capture('kernel',['uname','-a'])
hashes={}
if label=='first':
    hashes=dict(line.split()[1:] and (line.split()[1],line.split()[0]) for line in capture('partition-hashes',['sha256sum','/dev/sde11','/dev/sde32']).splitlines())
    capture('nv-check',['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
report=dict(stage=166,kernel_build=166 if version.startswith('#166 ') else version,
            uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
            same_boot_during_capture=True,desktop_process_count=len(desktop.strip().splitlines()),
            faults={key:len(re.findall(pattern,log)) for key,pattern in {
                'warnings':r'WARNING:','dma_prepare':r'unable to prepare channel',
                'tx_timeout':r'TX timed out','queue_exhaustion':r'Message buffer unavailable',
                'suspend_rejected':r'NGD suspend rejected','resume_failed':r'NGD resume failed',
                'wcd_efuse_incomplete':r'Efuse sense is not complete','codec_init_failed':r'Failed to initialize WCD934x hardware',
                'gpu_fault':r'gpu fault:','display_timeout':r'CTL.*timeout|DSI.*timeout'}.items()},
            wcd_version_valid='Version:0x411' in log,partition_hashes=hashes)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k166-'+label+'-runtime-private.tar.gz','w:gz') as archive:
    archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
