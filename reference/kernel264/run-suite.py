"""Run phone tests sequentially; stop on any functional or cleanup failure."""
from pathlib import Path
import json,subprocess,sys
R=Path(__file__).parent
for mode in [6000059,6000060,6000061,6000062,6000063]:
 q=subprocess.run([sys.executable,str(R/'run.py'),str(mode)],capture_output=True,timeout=145)
 if q.returncode:
  print(q.stdout.decode(errors='replace')[-1200:]+q.stderr.decode(errors='replace')[-1200:],flush=True);raise SystemExit(q.returncode)
 d=json.loads(q.stdout);p=d['probe_result']
 print(json.dumps(dict(mode=mode,completed=d['diagnostic_completed'],failure=p['failure'],frames=[r['buffers'] for r in p['clients']],checked=sum(r['held_checked'] for r in p['clients']),changed=sum(r['held_content_changed'] for r in p['clients']),pts_increasing=all(r['pts_strictly_increasing'] for r in p['clients']),fd_counts=p['fd_counts'])),flush=True)
 if not d['diagnostic_completed']:raise SystemExit(1)
