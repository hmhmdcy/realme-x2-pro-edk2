from pathlib import Path
import json
import host

pid=int((host.PRIVATE/'geoclue-worker-pid-private.txt').read_text().strip())
native="""from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k207r2-gnss-context/boot-id-private.txt').read_bytes()
out=root/'k207r2-geoclue-first-session';p=Path('/proc/%d');running=p.exists() and b'test-geoclue-first-session.py' in (p/'cmdline').read_bytes();r=dict(running=running,summary_present=(out/'summary.json').exists())
if (out/'summary.json').exists():r['result']=json.loads((out/'summary.json').read_text())
elif (out/'progress.json').exists():
 v=json.loads((out/'progress.json').read_text());r['progress']={k:v[k] for k in ['ggatime_distinct','unique_nmea','valid_gga','positive_cnr_fields','automatic_worker_observed']}
print(json.dumps(r))
"""%pid
p=host.ssh('python3 -',input=native.encode(),timeout=20);(host.PRIVATE/'gnss-last-observation-private.json').write_bytes(p.stdout);r=json.loads(p.stdout)
if not r['running'] and r['summary_present']:(Path(__file__).resolve().parent/'geoclue-first-session-validation.json').write_text(json.dumps(r['result'],indent=2)+'\n')
print(json.dumps(r))
