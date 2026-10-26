from pathlib import Path
import json
import host

code = '''from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai/k188-ssc-pm')
trace=Path('/sys/kernel/tracing/instances/k188-ssc-pm')
report={}
if trace.exists() and (trace/'tracing_on').read_text().strip()=='0':
 stats={p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
 (root/'per-cpu-stats-recovered-private.json').write_text(json.dumps(stats))
 report['recovered_trace_cpus']=len(stats)
p=Path('/var/lib/samurai/k188-tools/pm-worker-exit.txt')
report['worker_exit']=int(p.read_text()) if p.exists() else None
if (root/'validation.json').exists():report['validation']=json.loads((root/'validation.json').read_text())
if (root/'phase-private.json').exists():report['phase']=json.loads((root/'phase-private.json').read_text())['phase']
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'suspend-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
