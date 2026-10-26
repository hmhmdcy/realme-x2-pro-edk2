"""Launch/inspect/fetch one bounded hotplug observer in the owned window."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shlex
import sys

ref = Path(__file__).resolve().parent
transaction = sys.argv[2] if len(sys.argv) > 2 else 'r1'
assert re.fullmatch(r'r[1-9][0-9]*', transaction), transaction
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023') / ('usb-hotplug-' + transaction)
out.mkdir(parents=True, exist_ok=True, mode=0o700)
remote = '/root/charging-management-20261023/usb-hotplug-' + transaction
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
action = sys.argv[1]

def query(code, **kwargs):
    response = window.host.ssh('python3 -c ' + shlex.quote(code), timeout=35, check=False, **kwargs)
    (out / (action + '-stdout-private.json')).write_bytes(response.stdout)
    (out / (action + '-stderr-private.txt')).write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-3000:])
        response.check_returncode()
    return json.loads(response.stdout)

if action == 'launch':
    files = {'worker.py': (ref / 'usb-hotplug.py').read_text(),
             'health-helper.py': (ref / 'charging-health.py').read_text()}
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}
    tests = json.loads((ref / 'usb-hotplug-test-result.json').read_text())
    assert tests['passed'] and tests['tested_files']['usb-hotplug.py'] == hashes['worker.py']
    tests = json.loads((ref / 'health-observer-test-result.json').read_text())
    assert tests['passed'] and tests['tested_files']['charging-health.py'] == hashes['health-helper.py']
    config = {'files': hashes, 'max_seconds': 600,
              'guard': '/var/lib/samurai/k449-adopted/boot-id-private.txt',
              'manifest_sha256': hashlib.sha256((out.parent / 'service/manifest.json').read_bytes()).hexdigest(),
              'monitor_ui': transaction == 'r4'}
    if transaction == 'r4':
        updated = json.loads((ref / 'ui-link-update-result.json').read_text())
        assert updated['passed'] and updated['new_manifest_sha256'] == config['manifest_sha256']
    for name, text in files.items(): (out / name).write_text(text)
    with (out / 'launch-request.json').open('x') as stream: json.dump(config, stream)
    payload = json.dumps({'files': files, 'config': config}).encode()
    code = """from pathlib import Path
import hashlib,json,os,subprocess,sys
os.umask(0o077);data=json.loads(sys.stdin.buffer.read())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(data['config']['guard']).read_bytes()
directory=Path(REMOTE);directory.mkdir(mode=0o700)
for name,text in data['files'].items():
 assert name in ['worker.py','health-helper.py']
 assert hashlib.sha256(text.encode()).hexdigest()==data['config']['files'][name]
 (directory/name).write_text(text)
(directory/'config.json').write_text(json.dumps(data['config']))
with (directory/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(directory/'worker.py'),str(directory)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(directory/'worker.pid').write_text(str(child.pid))
print(json.dumps({'launched':True,'pid':child.pid,'max_seconds':data['config']['max_seconds']}))
""".replace('REMOTE', repr(remote))
    print(json.dumps(query(code, input=payload)))
elif action in ['observe', 'fetch']:
    code = """from pathlib import Path
import json
p=Path(REMOTE)
def load(name):
 f=p/name
 return json.loads(f.read_text()) if f.exists() else None
status=load('status.json');pid=int((p/'worker.pid').read_text())
cmd=Path('/proc')/str(pid)/'cmdline'
alive=cmd.exists() and str(p/'worker.py').encode() in cmd.read_bytes().split(bytes([0]))
data={'status':status,'alive':alive,'result':load('result.json'),
 'failure':(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None,
 'log_tail':(p/'worker-private.log').read_text()[-3000:]}
if FETCH and (p/'capture-private.json').exists():data['capture']=load('capture-private.json')
print(json.dumps(data))
""".replace('REMOTE', repr(remote)).replace('FETCH', repr(action == 'fetch'))
    data = query(code)
    if action == 'fetch' and data.get('capture'):
        (out / 'capture-private.json').write_text(json.dumps(data['capture']))
        spec = importlib.util.spec_from_file_location('hotplug', out / 'worker.py')
        hotplug = importlib.util.module_from_spec(spec); spec.loader.exec_module(hotplug)
        result = hotplug.audit(data['capture'])
        assert result == data['result']
        result.update({'collector_sha256': hashlib.sha256((out / 'worker.py').read_bytes()).hexdigest(),
                       'private_capture_sha256': hashlib.sha256((out / 'capture-private.json').read_bytes()).hexdigest(),
                       'worker_exited': not data['alive']})
        (ref / 'usb-hotplug-result.json').write_text(json.dumps(result, indent=2) + '\n')
        (ref / ('usb-hotplug-' + transaction + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({key: data[key] for key in ['status', 'alive', 'result', 'failure', 'log_tail']}, indent=2))
else:
    raise ValueError(action)
