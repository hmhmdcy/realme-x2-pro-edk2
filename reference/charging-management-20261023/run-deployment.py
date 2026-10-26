"""Stage/install/test the precise charging service payload; no flash action."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window6')
private.mkdir(mode=0o700,exist_ok=True)
remote='/root/charging-management-20261023'
action=sys.argv[1]

def query(code,timeout=30):
    q=w.host.ssh('python3 -c '+shlex.quote(code),timeout=timeout,check=False)
    (private/(action+'-stdout-private.json')).write_bytes(q.stdout)
    (private/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:print(q.stderr.decode(errors='replace')[-2500:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

if action=='stage':
    payload=private.parent/'service/samurai-charging-payload.tar.gz'
    expected=json.loads((ref/'service-payload-result.json').read_text())
    assert hashlib.sha256(payload.read_bytes()).hexdigest()==expected['payload_sha256']
    files={'service-payload.tar.gz':payload,'deploy-service.py':ref/'deploy-service.py','live-session.py':ref/'live-session.py'}
    hashes={}
    for name,p in files.items():
        code='from pathlib import Path;import sys;p=Path('+repr(remote+'/'+name)+');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)'
        w.host.ssh('python3 -c '+shlex.quote(code),input=p.read_bytes(),timeout=25).check_returncode()
        q=w.host.ssh('sha256sum '+shlex.quote(remote+'/'+name),timeout=15);q.check_returncode()
        digest=q.stdout.decode().split()[0];assert digest==hashlib.sha256(p.read_bytes()).hexdigest();hashes[name]=digest
    (private/'staged.json').write_text(json.dumps(hashes,indent=2));print(json.dumps(hashes))
elif action in ['install','enable']:
    code='import runpy,sys;sys.argv=["deploy-service.py",'+repr(action)+'];runpy.run_path('+repr(remote+'/deploy-service.py')+',run_name="__main__")'
    print(json.dumps(query(code)))
elif action=='test':
    code="""from pathlib import Path
import subprocess,json
p=Path('/root/charging-management-20261023');assert not (p/'service-test').exists()
with (p/'service-test-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p/'deploy-service.py'),'test'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid}))
"""
    assert not (private/'test-request.json').exists();(private/'test-request.json').write_text('{"request_count":1}')
    print(json.dumps(query(code)))
elif action=='observe':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023');s=p/'service-test/state-private.json'
print(json.dumps({'state':json.loads(s.read_text()) if s.exists() else None,'log':(p/'service-test-worker.log').read_text()[-4000:]}))
"""
    print(json.dumps(query(code),indent=2))
elif action=='fetch':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023/service-test')
print(json.dumps({x.name:json.loads(x.read_text()) for x in p.glob('*.json')}))
"""
    data=query(code)
    for name,d in data.items():(private/name).write_text(json.dumps(d,indent=2))
    state=dict(data['state-private.json']);state.pop('pid',None)
    assert state['terminal']
    state['payload_sha256']=json.loads((ref/'service-payload-result.json').read_text())['payload_sha256']
    (ref/'service-test-result.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
else:raise ValueError(action)
