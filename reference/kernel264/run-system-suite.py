from pathlib import Path
import json,subprocess,sys
R=Path(__file__).parent
for mode in range(6000070,6000075):
 q=subprocess.run([sys.executable,str(R/'run-system.py'),str(mode)],capture_output=True,timeout=145)
 if q.returncode:print(q.stdout.decode(errors='replace')[-1200:]+q.stderr.decode(errors='replace')[-1200:],flush=True);raise SystemExit(q.returncode)
 d=json.loads(q.stdout);p=d['probe_result'];print(json.dumps(dict(mode=mode,completed=d['diagnostic_completed'],failure=p['failure'],frames=[r['buffers'] for r in p['clients']],checked=sum(r['held_checked'] for r in p['clients']),changed=sum(r['held_content_changed'] for r in p['clients']),image_done=any(r.get('image_done_message',False) for r in p['clients']))),flush=True)
 if not d['diagnostic_completed']:raise SystemExit(1)
