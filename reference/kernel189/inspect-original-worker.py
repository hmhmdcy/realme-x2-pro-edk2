from pathlib import Path
import json
import host

pid=int((host.PRIVATE/'original-freezer-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
pid=PID
root=Path('/var/lib/samurai/k189-freezer-original')
p=Path('/proc')/str(pid)
report=dict(worker_present=p.exists(),worker_cmdline=p.joinpath('cmdline').read_bytes().decode(errors='replace') if p.exists() else None)
for name in ['trial-exit.txt','start-exit.txt','userspace-exit.txt','stop-exit.txt']:
 if (root/name).exists():report[name]=(root/name).read_text().strip()
if (root/'userspace/summary.json').exists():report['case']=json.loads((root/'userspace/summary.json').read_text())
if (root/'userspace-run-private.txt').exists():
 raw=(root/'userspace-run-private.txt').read_text()
 report['python_failure']=raw if 'Traceback' in raw else None
report['slpi']=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()
print(json.dumps(report))
'''.replace('PID',str(pid))
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'original-worker-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
