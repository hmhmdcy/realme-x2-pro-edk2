from pathlib import Path
import json
import host
pid=int((host.PRIVATE/'diagnostic-worker-pid-private.txt').read_text().strip())
code="""from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes()
out=root/'k205-diagnostic-cycles';p=Path('/proc/%d');running=p.exists() and b'test-diagnostic-cycles.py' in (p/'cmdline').read_bytes();r=dict(running=running,summary_present=(out/'summary.json').exists())
if (out/'summary.json').exists():r['result']=json.loads((out/'summary.json').read_text())
elif (out/'progress.json').exists():r['progress']=json.loads((out/'progress.json').read_text())
print(json.dumps(r))
"""%pid
p=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'diagnostic-cycle-latest-private.json').write_bytes(p.stdout);r=json.loads(p.stdout)
if not r['running'] and r['summary_present']:(Path(__file__).resolve().parent/'diagnostic-cycles-validation.json').write_text(json.dumps(r['result'],indent=2)+'\n')
print(json.dumps(r))
