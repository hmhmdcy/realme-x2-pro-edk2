from pathlib import Path
import json
import host

host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
pid=int((host.PRIVATE/'persistent-pm-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
pid=PID
root=Path('/var/lib/samurai/k189-ssc-pm');process=Path('/proc')/str(pid)
report=dict(worker_present=process.exists())
if process.exists():report['worker_cmdline']=process.joinpath('cmdline').read_bytes().decode(errors='replace')
exitfile=Path('/var/lib/samurai/k189-tools/pm-worker-exit.txt')
if exitfile.exists():report['worker_exit']=int(exitfile.read_text())
if (root/'phase-private.json').exists():report['phase']=json.loads((root/'phase-private.json').read_text())['phase']
if (root/'validation.json').exists():report['validation']=json.loads((root/'validation.json').read_text())
if exitfile.exists() and exitfile.read_text().strip()!='0':
 raw=Path('/var/lib/samurai/k189-tools/pm-worker-private.log').read_text()
 report['worker_failure']=raw if 'Traceback' in raw else 'Nonzero without Python traceback'
print(json.dumps(report))
'''.replace('PID',str(pid))
p=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'pm-worker-inspection-private.json').write_bytes(p.stdout)
report=json.loads(p.stdout)
if 'validation' in report:
 (Path(__file__).resolve().parent/'persistent-suspend-validation.json').write_text(json.dumps(report['validation'],indent=2)+'\n')
print(p.stdout.decode())
