from pathlib import Path
import host,json
pid=int((host.PRIVATE/'utc-worker-pid-private.txt').read_text().strip())
native=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes()
out=root/'k209-clock-compare';p=Path('/proc/PID_PLACEHOLDER')
running=p.exists() and b'/var/lib/samurai/k209-tools/compare-utc-precision.py' in (p/'cmdline').read_bytes()
report=dict(running=running,summary_present=(out/'summary.json').exists())
if report['summary_present']:report['result']=json.loads((out/'summary.json').read_text())
elif (out/'progress.json').exists():
    value=json.loads((out/'progress.json').read_text());report['progress']={name:value[name] for name in ['engine_states','utc_exchanges','phases','errors','proposed_clock_bound'] if name in value}
print(json.dumps(report))
'''.replace('PID_PLACEHOLDER',str(pid))
p=host.ssh('python3 -',input=native.encode(),timeout=25)
(host.PRIVATE/'utc-last-observation-private.json').write_bytes(p.stdout)
value=json.loads(p.stdout)
if not value['running'] and value['summary_present']:(Path(__file__).resolve().parent/'utc-comparison-validation.json').write_text(json.dumps(value['result'],indent=2)+'\n')
print(json.dumps(value))
