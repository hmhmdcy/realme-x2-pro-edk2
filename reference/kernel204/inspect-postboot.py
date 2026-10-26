from pathlib import Path
import json,os,subprocess

root=Path('/var/lib/samurai');out=root/'k204-postboot-inspection';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
commands={'services':['rc-status','--all'],'ssc-status':['rc-service','samurai-ssc','status'],'ssc-init':['cat','/etc/init.d/samurai-ssc'],'sensor-status':['rc-service','iio-sensor-proxy','status'],'processes':['ps','-ef'],'dmesg':['dmesg'],'uart-pinctrl':['sh','-c','cat /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins'],'interrupts':['cat','/proc/interrupts'],'ssc-logs':['sh','-c','find /run/samurai* /var/log -maxdepth 3 -type f -name "*ssc*" -o -name "*slpi*" -o -name "*hexagon*"']}
codes={}
for name,args in commands.items():
 p=subprocess.run(args,capture_output=True,timeout=15);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr);codes[name]=p.returncode
for path in ['/usr/sbin/samurai-ssc','/var/log/samurai-ssc.log','/run/samurai-ssc/state.json']:
 p=Path(path)
 if p.is_file():(out/(p.name+'-copy-private')).write_bytes(p.read_bytes())
log=(out/'dmesg-private.txt').read_text();bt=[l[l.index('Frame reassembly failed'):] for l in log.splitlines() if 'Frame reassembly failed' in l]
r=dict(stage=204,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),same_new_boot=True,service_returncodes=codes,bluetooth_error_details=bt,remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')})
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
