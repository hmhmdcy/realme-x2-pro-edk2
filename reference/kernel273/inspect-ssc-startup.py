from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
p=Path('/run/samurai-ssc/state.json');record=json.loads(p.read_text()) if p.exists() else {}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
logs={str(p):p.read_text(errors='replace')[-30000:] for p in Path('/run/samurai-ssc').glob('*') if p.is_file() and p.suffix in ['.log','.txt']}
report=dict(state_present=bool(record),attempted=record.get('attempted'),started=record.get('started'),
 current_boot_matches=record.get('boot_id')==boot if record else None,
 remoteprocs={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')},
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),logs=logs,
 status=subprocess.run(['rc-status','default'],capture_output=True,text=True).stdout)
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'ssc-startup-inspection-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);d.pop('logs');print(json.dumps(d,indent=2))
