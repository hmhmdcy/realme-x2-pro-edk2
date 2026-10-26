"""Try the previously authenticated endpoint once; never weaken host checks."""
from pathlib import Path
import importlib.util,json,subprocess,time
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('strict184',HERE.parent/'kernel184/host.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
selected=json.loads((host.PRIVATE.parent/'kernel303/fresh-working-endpoint-private.json').read_text());assert selected['kind']=='wifi'
start=time.monotonic()
try:
 q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+selected['IPAddress'],
    'uname -r; cat /proc/uptime; cat /var/lib/samurai/k366-boot-r1/state.json'],capture_output=True,timeout=15)
 (host.PRIVATE/'wifi-probe-private.log').write_bytes(q.stdout+q.stderr)
 print(json.dumps(dict(authenticated=q.returncode==0,exit_code=q.returncode,seconds=round(time.monotonic()-start,2))))
except subprocess.TimeoutExpired as e:
 (host.PRIVATE/'wifi-probe-private.log').write_bytes((e.stdout or b'')+(e.stderr or b''));print(json.dumps(dict(authenticated=False,timeout=True)))
