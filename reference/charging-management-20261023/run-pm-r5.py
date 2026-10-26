"""A new targeted PM check after the charger update; old transactions stay intact."""
from pathlib import Path
import importlib.util
import json
import shlex
import sys

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pm-r5'); out.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
action = sys.argv[1]
if action == 'launch':
    worker = (ref / 'charging-pm.py').read_text().replace("out=ROOT/'charging-pm';", "out=ROOT/'charging-pm-r5';")
    worker = worker.replace('instances/charging-pm-20261023', 'instances/charging-pm-r5-20261023')
    marker = "assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'"
    worker = worker.replace(marker, marker + "\nimport hashlib\nassert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf'")
    (out / 'worker.py').write_text(worker)
    with (out / 'launch-request.json').open('x') as f: json.dump({'count': 1}, f)
    code = '''from pathlib import Path
import json,os,subprocess,sys
os.umask(0o077);p=Path('/root/charging-management-20261023/charging-pm-r5.py');assert not p.exists();p.write_bytes(sys.stdin.buffer.read())
with p.with_suffix('.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
p.with_suffix('.pid').write_text(str(child.pid));print(json.dumps({'launched':True,'pid':child.pid}))
'''
    payload = worker.encode()
elif action == 'fetch':
    payload = None
    code = '''from pathlib import Path
import json
p=Path('/root/charging-management-20261023/charging-pm-r5');script=p.with_suffix('.py');pid=int(p.with_suffix('.pid').read_text());cmd=Path('/proc')/str(pid)/'cmdline'
alive=cmd.exists() and str(script).encode() in cmd.read_bytes().split(bytes([0]))
files={x.name:x.read_text() for x in p.iterdir() if x.is_file()}
print(json.dumps({'alive':alive,'files':files,'log':p.with_suffix('.log').read_text()[-2000:]}))
'''
else: raise ValueError(action)
q = window.host.ssh('python3 -c ' + shlex.quote(code), input=payload, timeout=30, check=False)
(out / (action + '-stdout-private.json')).write_bytes(q.stdout)
(out / (action + '-stderr-private.txt')).write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2500:]); raise SystemExit(q.returncode)
data = json.loads(q.stdout)
if action == 'fetch':
    for n, content in data['files'].items():
        assert '/' not in n; (out / n).write_text(content)
    print(json.dumps({'alive': data['alive'], 'phase': json.loads(data['files'].get('phase-private.json', 'null')),
                      'result': json.loads(data['files'].get('runtime-result.json', 'null')), 'log': data['log']}, indent=2))
else: print(json.dumps(data))
