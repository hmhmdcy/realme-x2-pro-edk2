"""Remove only the owned temporary startup hook after its capture is terminal."""
from pathlib import Path
import hashlib,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();base=r/'k247-nextboot';s=json.loads((base/'capture/state-private.json').read_text());assert s['terminal'] and s['exit_code']==0 and not Path('/proc',str(s['pid'])).exists()
service=Path('/etc/init.d/samurai-diag247');hashes=json.loads((base/'installed-source-hashes.json').read_text());assert hashlib.sha256(service.read_bytes()).hexdigest()==hashes['samurai-diag247.initd']
x=subprocess.run(['rc-update','del','samurai-diag247','default'],capture_output=True,check=True);service.unlink();pid=Path('/run/samurai-diag247.pid')
if pid.exists():assert int(pid.read_text())==s['pid'];pid.unlink()
assert not service.exists() and not Path('/etc/runlevels/default/samurai-diag247').exists()
print(json.dumps(dict(stage=247,temporary_hook_removed=True,private_capture_retained=True,daemon_terminal=True,no_process_killed=True)))
