from pathlib import Path
import json
import host

pid=int((host.PRIVATE/'mm-stream-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
pid=PID;proc=Path('/proc')/str(pid);out=Path('/var/lib/samurai/k190-mm-stream')
report=dict(worker_present=proc.exists())
if proc.exists():
 cmd=proc.joinpath('cmdline').read_bytes();report['worker_identity_matches']=b'test-mm-location-stream.py' in cmd
done=Path('/var/lib/samurai/k190-tools/mm-stream-worker-exit.txt')
if done.exists():report['worker_exit']=int(done.read_text())
if (out/'summary.json').exists():report['validation']=json.loads((out/'summary.json').read_text())
if done.exists() and done.read_text().strip()!='0':
 raw=Path('/var/lib/samurai/k190-tools/mm-stream-worker-private.log').read_text()
 report['failure_has_traceback']='Traceback' in raw
print(json.dumps(report))
'''.replace('PID',str(pid))
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'mm-stream-inspection-private.json').write_bytes(p.stdout)
report=json.loads(p.stdout)
if 'validation' in report:(Path(__file__).resolve().parent/'mm-location-stream-validation.json').write_text(json.dumps(report['validation'],indent=2)+'\n')
print(json.dumps(report))
