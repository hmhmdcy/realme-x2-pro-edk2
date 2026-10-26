"""Launch once, then fetch the independent USB re-enumeration transaction."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-reenumerate')
out.mkdir(exist_ok=True)
remote = '/root/charging-management-20261023/usb-reenumerate'
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
action = sys.argv[1]
if action == 'launch':
    files = {'worker.py': (ref / 'usb-reenumerate.py').read_text(),
             'health.py': (ref / 'charging-health.py').read_text(),
             'events.py': (ref / 'usb-hotplug.py').read_text()}
    config = {'guard': '/var/lib/samurai/k449-adopted/boot-id-private.txt',
              'manifest_sha256': hashlib.sha256((out.parent / 'service/manifest.json').read_bytes()).hexdigest()}
    payload = json.dumps({'files': files, 'config': config}).encode()
    with (out / 'launch-request.json').open('x') as f: json.dump(config, f)
    for n, content in files.items(): (out / n).write_text(content)
    code = '''from pathlib import Path
import json,os,subprocess,sys
os.umask(0o077);data=json.loads(sys.stdin.buffer.read());d=Path(REMOTE);d.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(data['config']['guard']).read_bytes()
for n,content in data['files'].items():
 assert n in ['worker.py','health.py','events.py'];(d/n).write_text(content)
(d/'config.json').write_text(json.dumps(data['config']))
with (d/'worker-private.log').open('xb') as log:
 p=subprocess.Popen(['python3',str(d/'worker.py'),str(d)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(d/'worker.pid').write_text(str(p.pid));print(json.dumps({'launched':True,'pid':p.pid}))
'''.replace('REMOTE', repr(remote))
elif action == 'fetch':
    payload = None
    code = '''from pathlib import Path
import json
d=Path(REMOTE);pid=int((d/'worker.pid').read_text());p=Path('/proc')/str(pid)/'cmdline'
alive=p.exists() and str(d/'worker.py').encode() in p.read_bytes().split(bytes([0]))
print(json.dumps({'alive':alive,'capture':json.loads((d/'capture-private.json').read_text()) if (d/'capture-private.json').exists() else None,'log':(d/'worker-private.log').read_text()[-3000:]}))
'''.replace('REMOTE', repr(remote))
else: raise ValueError(action)
q = window.host.ssh('python3 -c ' + shlex.quote(code), input=payload, timeout=35, check=False)
(out / (action + '-stdout-private.json')).write_bytes(q.stdout)
(out / (action + '-stderr-private.txt')).write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2500:]); raise SystemExit(q.returncode)
data = json.loads(q.stdout)
if data.get('capture'):
    (out / 'capture-private.json').write_text(json.dumps(data['capture']))
    result = data['capture']['result']; result['worker_exited'] = not data['alive']
    (ref / 'usb-reenumerate-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
else: print(json.dumps(data, indent=2))
