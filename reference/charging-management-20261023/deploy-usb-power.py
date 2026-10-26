"""Install only the two USB script edits and launch the detached watcher.
The active 100mA descriptor stays unchanged until the user unplugs the cable.
"""
from pathlib import Path
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-power500')
request = json.loads((out / 'request-private.json').read_text())
request['worker'] = (ref / 'usb-power-detached.py').read_text()
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
with (out / 'deploy-request.json').open('x') as stream: json.dump({'count': 1}, stream)
code = """from pathlib import Path
import hashlib,json,os,subprocess,sys
os.umask(0o077);request=json.loads(sys.stdin.buffer.read())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(request['guard']).read_bytes()
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()==request['manifest_sha256']
directory=Path('/root/charging-management-20261023/usb-power500');directory.mkdir(mode=0o700)
changed=[]
try:
 for name,entry in request['files'].items():
  p=Path(name);assert not p.is_symlink() and str(p.resolve())==entry['canonical']
  assert p.stat().st_uid==0 and p.stat().st_mode & 0o777 == 0o755
  assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['before_sha256']
  backup=directory/('local-before.sh' if '/local/' in name else 'diagnostic-before.sh')
  backup.write_bytes(p.read_bytes())
  assert hashlib.sha256(entry['text'].encode()).hexdigest()==entry['after_sha256']
  temporary=p.with_name(p.name+'.power500-next');assert not temporary.exists()
  with temporary.open('x') as f:f.write(entry['text']);f.flush();os.fsync(f.fileno())
  temporary.chmod(0o755);temporary.replace(p);changed.append((p,backup))
  subprocess.run(['sh','-n',str(p)],check=True)
except BaseException:
 for p,backup in reversed(changed):p.write_bytes(backup.read_bytes());p.chmod(0o755)
 raise
(directory/'request-private.json').write_text(json.dumps({k:v for k,v in request.items() if k!='worker'}))
(directory/'worker.py').write_text(request['worker'])
with (directory/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(directory/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(directory/'worker.pid').write_text(str(child.pid))
print(json.dumps({'scripts_installed':True,'worker_pid':child.pid,
 'active_MaxPower_ma':int(Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text()),
 'native_budget_ua':int(Path('/sys/class/power_supply/samurai-usb-input/input_current_limit').read_text()),
 'charger_writes':0,'manifest_unchanged':True}))
"""
q = window.host.ssh('python3 -c ' + shlex.quote(code), input=json.dumps(request).encode(), timeout=35, check=False)
(out / 'deploy-stdout-private.json').write_bytes(q.stdout)
(out / 'deploy-stderr-private.txt').write_bytes(q.stderr)
if q.returncode: print(q.stderr.decode(errors='replace')); q.check_returncode()
result = json.loads(q.stdout)
(ref / 'usb-power-deploy-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
