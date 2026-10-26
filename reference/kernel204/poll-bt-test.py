from pathlib import Path
import json
import host

pid=int((host.PRIVATE/'bt-test-worker-pid-private.txt').read_text().strip())
code="""from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
out=root/'k204-bt-scan-pm-r2';p=Path('/proc/%d');running=p.exists() and b'test-bt-scan-pm.py' in (p/'cmdline').read_bytes()
report=dict(running=running,summary_present=(out/'summary.json').exists(),phase=json.loads((out/'powered-suspend/phase-private.json').read_text())['phase'] if (out/'powered-suspend/phase-private.json').exists() else None)
if (out/'summary.json').exists():report['result']=json.loads((out/'summary.json').read_text())
print(json.dumps(report))
"""%pid
p=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'bt-test-latest-observation-private.json').write_bytes(p.stdout);r=json.loads(p.stdout)
if not r['running'] and r['summary_present']:(Path(__file__).resolve().parent/'bluetooth-pm-validation.json').write_text(json.dumps(r['result'],indent=2)+'\n')
print(json.dumps(r))
