from pathlib import Path
import host
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
out=root/'k213-libcamera-build';active=json.loads((out/'active-build-private.json').read_text());process=Path('/proc')/str(active['pid'])
logs={p.name:'\n'.join(p.read_text(errors='replace').splitlines()[-12:]) for p in [out/'configure-helper-r2-private.log',out/'compile-helper-private.log'] if p.exists()}
print(json.dumps(dict(active_phase=active['phase'],recorded_pid_still_present=process.exists(),recorded_pid_command=(process/'comm').read_text().strip() if process.exists() else None,logs=logs)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'build-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
