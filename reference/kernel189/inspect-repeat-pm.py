from pathlib import Path
import json
import host

host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
pid=int((host.PRIVATE/'repeat-pm-worker-pid-private.txt').read_text())
code='''from pathlib import Path
import json
pid=PID;proc=Path('/proc')/str(pid);report=dict(worker_present=proc.exists(),cycles={})
if proc.exists():report['worker_cmdline']=proc.joinpath('cmdline').read_bytes().decode(errors='replace')
exitfile=Path('/var/lib/samurai/k189-tools/repeat-pm-worker-exit.txt')
if exitfile.exists():report['worker_exit']=int(exitfile.read_text())
for index in [2,3]:
 root=Path('/var/lib/samurai/k189-ssc-pm-r'+str(index));record={}
 if (root/'phase-private.json').exists():record['phase']=json.loads((root/'phase-private.json').read_text())['phase']
 if (root/'validation.json').exists():record['validation']=json.loads((root/'validation.json').read_text())
 report['cycles'][str(index)]=record
print(json.dumps(report))
'''.replace('PID',str(pid))
p=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'repeat-pm-inspection-private.json').write_bytes(p.stdout)
report=json.loads(p.stdout)
for index,record in report['cycles'].items():
 if 'validation' in record:
  (Path(__file__).resolve().parent/('persistent-suspend-r'+index+'-validation.json')).write_text(json.dumps(record['validation'],indent=2)+'\n')
print(p.stdout.decode())
