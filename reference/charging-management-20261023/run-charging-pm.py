"""Manual RTC PM worker entry point, only in a newly owned phone window."""
from pathlib import Path
import importlib.util
import json
import shlex
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
p=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pm')
p.mkdir(mode=0o700,exist_ok=True)
action=sys.argv[1]
remote='/root/charging-management-20261023'

def query(code):
    q=w.host.ssh('python3 -c '+shlex.quote(code),timeout=25,check=False)
    (p/(action+'-stdout-private.json')).write_bytes(q.stdout);(p/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

if action=='launch':
    assert not (p/'launch-request.json').exists()
    code="""from pathlib import Path
import subprocess,sys,json
p=Path('/root/charging-management-20261023/charging-pm.py');assert not p.exists();p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)
with p.with_name('charging-pm-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'launched_once':True}))
"""
    (p/'launch-request.json').write_text('{"request_count":1}')
    q=w.host.ssh('python3 -c '+shlex.quote(code),input=(ref/'charging-pm.py').read_bytes(),timeout=20)
    (p/'launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023/charging-pm');phase=p/'phase-private.json';r=p/'runtime-result.json'
print(json.dumps({'phase':json.loads(phase.read_text()) if phase.exists() else None,'result':json.loads(r.read_text()) if r.exists() else None,'failure':(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None}))
"""
    print(json.dumps(query(code),indent=2))
elif action=='fetch':
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023/charging-pm')
print(json.dumps({x.name:x.read_text() for x in p.iterdir() if x.is_file()}))
"""
    data=query(code)
    for name,text in data.items():assert '/' not in name;(p/name).write_text(text)
    result=json.loads(data['runtime-result.json'])
    (ref/'charging-pm-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
else:raise ValueError(action)
