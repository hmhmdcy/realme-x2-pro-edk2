"""Stage/launch/observe one bounded charging worker in an owned window."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
host=w.host
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window5')
private.mkdir(exist_ok=True,mode=0o700)
remote='/root/charging-management-20261023'
action=sys.argv[1]

def query(code,timeout=25):
    q=host.ssh('python3 -c '+shlex.quote(code),timeout=timeout,check=False)
    (private/(action+'-stdout-private.json')).write_bytes(q.stdout)
    (private/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

if action=='stage':
    manifest=json.loads((ref/'integrated-build-result.json').read_text())
    files={n:ref/n for n in ['control-trial.py','live-session.py']}
    for name,info in manifest['modules'].items():
        p=Path(info['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256']
        assert 'intree:         Y' in info['modinfo'];files[name+'.ko']=p
    hashes={}
    for name,p in files.items():
        data=p.read_bytes();target=remote+'/'+name
        code='from pathlib import Path;import sys;p=Path('+repr(target)+');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)'
        host.ssh('python3 -c '+shlex.quote(code),input=data,timeout=25).check_returncode()
        q=host.ssh('sha256sum '+shlex.quote(target),timeout=15);q.check_returncode()
        digest=q.stdout.decode().split()[0];assert digest==hashlib.sha256(data).hexdigest();hashes[name]=digest
    (private/'staged.json').write_text(json.dumps(hashes,indent=2));print(json.dumps(hashes))
elif action=='launch':
    code="""from pathlib import Path
import subprocess,json
p=Path('/root/charging-management-20261023');assert not (p/'control-trial').exists()
with (p/'control-trial-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p/'control-trial.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'launched_once':True}))
"""
    assert not (private/'launch-request.json').exists()
    (private/'launch-request.json').write_text(json.dumps({'request_count':1}))
    print(json.dumps(query(code)))
elif action=='observe':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023');s=p/'control-trial/state-private.json'
d=json.loads(s.read_text()) if s.exists() else None
stat=Path('/proc',str(d['pid']),'stat') if d else None
live=bool(stat and stat.exists() and stat.read_text().rsplit(')',1)[1].split()[0]!='Z')
print(json.dumps({'state':d,'worker_live':live,'log':(p/'control-trial-worker.log').read_text()[-4000:]}))
"""
    print(json.dumps(query(code),indent=2))
elif action=='fetch':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023/control-trial')
print(json.dumps({x.name:json.loads(x.read_text()) for x in p.glob('*.json')}))
"""
    data=query(code)
    for name,content in data.items(): (private/name).write_text(json.dumps(content,indent=2))
    state=data['state-private.json'];assert state['terminal']
    state.pop('pid',None)
    state['module_hashes']=json.loads((private/'staged.json').read_text())
    state['partitions_written']=[]
    (ref/'control-trial-result.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(state,indent=2))
else:raise ValueError(action)
