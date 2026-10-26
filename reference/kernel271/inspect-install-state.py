"""Inspect a submitted transaction without replaying it or exposing environments."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
o=Path('/var/lib/samurai/k271-gain-transaction')
d=dict(state=json.loads((o/'transaction-state-private.json').read_text()),failure=(o/'failure-private.txt').read_text() if (o/'failure-private.txt').exists() else None,
 processes=[],manager_logs={p.name:p.read_text() for p in o.glob('*manager-status-private.log')})
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber','phosh','phoc']:
   fields=(p/'stat').read_text().rsplit(')',1)[1].split();d['processes'].append(dict(name=name,pid=int(p.name),state=fields[0],start_ticks=fields[19]))
 except OSError:pass
d['module_bound']=Path('/sys/bus/i2c/devices/8-002d/driver').is_symlink()
d['kernel_gain_controls']=subprocess.check_output(['v4l2-ctl','-d',next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d'),'--list-ctrls'],text=True)
print(json.dumps(d))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'install-inspection-r1-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(json.dumps(d,indent=2))
