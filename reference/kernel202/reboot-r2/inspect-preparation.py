from pathlib import Path
import importlib.util,json,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel202/reboot-r2')
spec=importlib.util.spec_from_file_location('usb188',here.parent.parent/'kernel188/host.py');usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb);usb.PRIVATE=private
native=r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k202r2-preparation-inspection';assert not out.exists();out.mkdir(mode=0o700)
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
for name in ['prepare-time-stdout-private.json','prepare-time-stderr-private.txt','watch-stderr-private.log']:
 source=root/'gnss-assist'/name
 if source.exists():(out/name).write_bytes(source.read_bytes())
p=subprocess.run(['chronyc','tracking'],capture_output=True,text=True,timeout=10);(out/'chrony-private.txt').write_text(p.stdout+p.stderr)
r=dict(stage=202,reboot_cycle=2,current_boot_verified=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),chrony_normal=p.returncode==0 and 'Normal' in p.stdout,watch=watch,stderr_bytes=(out/'prepare-time-stderr-private.txt').stat().st_size if (out/'prepare-time-stderr-private.txt').exists() else None)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=usb.ssh('python3 -',input=native.encode(),timeout=35);(private/'preparation-inspection-private.json').write_bytes(p.stdout)
usb.download('/var/lib/samurai/k202r2-preparation-inspection/prepare-time-stderr-private.txt',private/'prepare-time-stderr-private.txt')
print(p.stdout.decode())
