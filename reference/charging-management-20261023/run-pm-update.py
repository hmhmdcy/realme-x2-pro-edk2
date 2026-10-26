"""Stage, launch and collect the bounded PM-link module update."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
p=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pm-update')
remote='/root/charging-management-20261023';action=sys.argv[1]

def query(code):
    q=w.host.ssh('python3 -c '+shlex.quote(code),timeout=25,check=False)
    (p/(action+'-stdout-private.json')).write_bytes(q.stdout);(p/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

if action=='stage':
    files={'pm-link-update.tar.gz':p/'pm-link-update.tar.gz','pm-link-update-lock.json':p/'update-lock.json','update-pm-links.py':ref/'update-pm-links.py'}
    for name,path in files.items():
        code='from pathlib import Path;import sys;p=Path('+repr(remote+'/'+name)+');assert not p.exists();p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)'
        w.host.ssh('python3 -c '+shlex.quote(code),input=path.read_bytes(),timeout=25).check_returncode()
    print(json.dumps({'staged':True,'modules_reloaded':False}))
elif action=='launch':
    assert not (p/'launch-request.json').exists();(p/'launch-request.json').write_text('{"count":1}')
    code="""from pathlib import Path
import subprocess,json
p=Path('/root/charging-management-20261023');assert not (p/'pm-link-update').exists()
with (p/'pm-link-update-worker.log').open('xb') as log:
 c=subprocess.Popen(['python3',str(p/'update-pm-links.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':c.pid}))
"""
    print(json.dumps(query(code)))
elif action in ['observe','fetch']:
    code="""from pathlib import Path
import json
p=Path('/root/charging-management-20261023');r=p/'pm-link-update/result.json'
print(json.dumps({'result':json.loads(r.read_text()) if r.exists() else None,'log':(p/'pm-link-update-worker.log').read_text()[-4000:],'failure':json.loads((r.parent/'failure-private.json').read_text()) if (r.parent/'failure-private.json').exists() else None}))
"""
    data=query(code);print(json.dumps(data,indent=2))
    if action=='fetch':
        assert data['result']['terminal']
        (ref/'pm-link-update-result.json').write_text(json.dumps(data['result'],indent=2)+'\n')
else:raise ValueError(action)
