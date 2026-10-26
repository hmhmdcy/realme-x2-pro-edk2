"""Wait three actual local source-only children; never transport or bind."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
HERE=Path(__file__).resolve().parent
records=[]
for name in ('host.py','remote.py','supervisor.py'):
    argv=[sys.executable,'-B',str(HERE/name)]
    started=time.time_ns();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();rc=child.wait()
    value=json.loads(stdout);assert rc==0 and not stderr and value['source_only'] is True
    assert not value.get('device_accessed',False) and not value.get('worker_started',False)
    records.append(dict(argv=argv,pid=child.pid,terminal=True,returncode=rc,started_ns=started,finished_ns=time.time_ns(),
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest(),source_sha256=hashlib.sha256((HERE/name).read_bytes()).hexdigest(),output=value))
result=dict(passed=True,commands=records,source_only=True,runtime_material_or_lease_generated=False,device_or_transport_accessed=False)
(HERE/'local-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result))
