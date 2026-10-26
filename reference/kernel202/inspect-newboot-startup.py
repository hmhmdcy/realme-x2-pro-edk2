from pathlib import Path
import importlib.util, json, subprocess

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('usb188', here.parent/'kernel188/host.py')
usb = importlib.util.module_from_spec(spec); spec.loader.exec_module(usb)
usb.PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel202')
native = r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');out=root/'k202-startup-inspection-r2';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k202-runtime/boot-id-private.txt').read_bytes() and boot!=(root/'k202-before-reboot/boot-id-private.txt').read_bytes();assert os.uname().version.startswith('#183 ')
results={}
for key,command in [('status',['rc-service','samurai-gnss-assist','status']),('all',['rc-status','-a']),('processes',['ps','-eo','pid,ppid,user,args'])]:
 p=subprocess.run(command,capture_output=True,text=True,timeout=15);(out/(key+'-private.txt')).write_text(p.stdout+p.stderr);results[key]=p.returncode
state=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
for name in ['watch-stdout-private.log','watch-stderr-private.log']:
 (out/name).write_bytes((root/'gnss-assist'/name).read_bytes())
r=dict(stage=202,current_new_boot_verified=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),service_status_returncode=results['status'],watch_running=state['running'],watch_active=state['active'],worker_starts=state['worker_starts'],worker_completions=state['worker_completions'],pidfile_exists=Path('/run/samurai-gnss-assist.pid').exists(),default_runlevel_symlink_present=Path('/etc/runlevels/default/samurai-gnss-assist').is_symlink(),stderr_bytes=(out/'watch-stderr-private.log').stat().st_size,init_executable=Path('/proc/1/exe').resolve().name)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
try:
    p=usb.ssh('python3 -', input=native.encode(), timeout=45)
except subprocess.CalledProcessError as e:
    (usb.PRIVATE/'startup-inspection-failed-private.log').write_bytes((e.stdout or b'')+(e.stderr or b''))
    raise SystemExit('Authenticated startup inspection failed; no transition repeated')
(usb.PRIVATE/'startup-inspection-private.json').write_bytes(p.stdout)
usb.download('/var/lib/samurai/k202-startup-inspection-r2/watch-stderr-private.log',usb.PRIVATE/'startup-watch-stderr-private.log')
usb.download('/var/lib/samurai/k202-startup-inspection-r2/all-private.txt',usb.PRIVATE/'startup-services-private.txt')
usb.download('/var/lib/samurai/k202-startup-inspection-r2/status-private.txt',usb.PRIVATE/'startup-status-private.txt')
print(p.stdout.decode())
