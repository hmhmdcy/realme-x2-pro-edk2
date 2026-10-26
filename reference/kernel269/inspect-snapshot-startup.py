"""Read diagnostics for the single recorded startup without rerunning it."""
from pathlib import Path
import importlib.util,json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,pwd,subprocess
p=Path('/var/lib/samurai/k269-snapshot-startup-r1');u=pwd.getpwuid(10000)
print(json.dumps(dict(app_log=(p/'snapshot-private.log').read_text(errors='replace'),
 session_log=Path(u.pw_dir,'.local/state/samurai-phosh-session.log').read_text(errors='replace')[-20000:],
 pipeline_services=subprocess.run(['rc-status','default'],capture_output=True,text=True).stdout)))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=20);(P/'snapshot-startup-diagnostics-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(d['app_log'][-7000:])
print('\n'.join(l for l in d['session_log'].splitlines() if any(k in l.lower() for k in ['camera','pipewire','sensor-proxy','acceleromet','fatal','error','failed','critical']))[-5000:])
