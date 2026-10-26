"""Remove the unaccepted 500mA startup migration after verified live rollback."""
from pathlib import Path
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-reenumerate')
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
code = '''from pathlib import Path
import hashlib,json,os,subprocess
d=Path('/root/charging-management-20261023/usb-power500')
request=json.loads((d/'request-private.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(request['guard']).read_bytes()
result=json.loads(Path('/root/charging-management-20261023/usb-reenumerate/result.json').read_text())
assert result['terminal'] and not result['native_host_budget_accepted'] and result['MaxPower_ma']==100
assert Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='100'
changed=[]
for name,entry in request['files'].items():
 p=Path(name);backup=d/('local-before.sh' if '/local/' in name else 'diagnostic-before.sh')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['after_sha256']
 assert hashlib.sha256(backup.read_bytes()).hexdigest()==entry['before_sha256']
 tmp=p.with_name(p.name+'.restore100-next');assert not tmp.exists()
 with tmp.open('xb') as f:f.write(backup.read_bytes());f.flush();os.fsync(f.fileno())
 tmp.chmod(0o755);tmp.replace(p);subprocess.run(['sh','-n',str(p)],check=True)
 changed.append({'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
meta=subprocess.run(['apk','info','-W','/usr/bin/phosh','/usr/libexec/upowerd'],capture_output=True,text=True)
print(json.dumps({'restored':changed,'MaxPower_ma':100,'native_allowance_ua':int(Path('/sys/class/power_supply/samurai-usb-input/input_current_limit').read_text()),'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'package_versions':meta.stdout+meta.stderr}))
'''
q = window.host.ssh('python3 -c ' + shlex.quote(code), timeout=35, check=False)
(out / 'restore-scripts-stdout-private.json').write_bytes(q.stdout)
(out / 'restore-scripts-stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2500:]); raise SystemExit(q.returncode)
result = json.loads(q.stdout)
(ref / 'usb-startup-rollback-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
