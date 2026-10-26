"""Read current power/UI metadata using the existing pinned transport."""
from pathlib import Path
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/ui-current')
out.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
code = '''from pathlib import Path
import hashlib,json,subprocess
def read(p):
 try:return Path(p).read_text().strip()
 except OSError as e:return {'errno':e.errno}
def command(args):
 q=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 return {'rc':q.returncode,'text':q.stdout}
root=Path('/sys/class/power_supply')
data={'supplies':{p.name:{n:read(p/n) for n in ['type','status','online','current_now','voltage_now','capacity','temp','usb_type','current_max','input_current_limit','supplied_to']} for p in root.iterdir()},
 'telemetry':read('/sys/bus/i2c/devices/0-005c/telemetry'),
 'MaxPower':read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower'),
 'UDC':read('/sys/kernel/config/usb_gadget/samurai/UDC'),
 'taint':read('/proc/sys/kernel/tainted'),
 'manifest_sha256':hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest(),
 'versions':command(['apk','info','-v','upower','phosh']),
 'upower':command(['upower','-d']),
 'upower_config':read('/etc/UPower/UPower.conf')}
print(json.dumps(data))
'''
q = window.host.ssh('python3 -c ' + shlex.quote(code), timeout=50, check=False)
(out / 'state-private.json').write_bytes(q.stdout)
(out / 'stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2000:]); raise SystemExit(q.returncode)
data = json.loads(q.stdout)
print(json.dumps(data, indent=2))
