from pathlib import Path
import json,sys
import host
R=Path(__file__).parent
delay=int(sys.argv[1]);assert delay in [0,40000,1000000,2000000,2000001,3000000,3000001,3000002,4000000,6000000]
source=(R/'pipewire-probe.py').read_text()
setup="from pathlib import Path;import os;os.umask(0o077);p=Path('/var/lib/samurai/k262-tools');p.mkdir(exist_ok=True);p.chmod(0o755);f=p/'pipewire-probe.py';f.write_text("+repr(source)+");f.chmod(0o644)"
host.ssh('python3 -',input=setup.encode())
if delay in [3000000,3000001,3000002,6000000]:
 upload="from pathlib import Path;import sys,os;p=Path('/var/lib/samurai/k262-candidate');p.mkdir(exist_ok=True);p.chmod(0o755);f=p/'libgstpipewire.so';f.write_bytes(sys.stdin.buffer.read());f.chmod(0o644);u=Path('/var/lib/samurai/k262-user');u.mkdir(mode=0o700,exist_ok=True);os.chown(u,10000,10000)"
 import shlex
 host.ssh('python3 -c '+shlex.quote(upload),input=(host.PRIVATE/({3000000:'libgstpipewire-candidate.so',6000000:'libgstpipewire-ownership.so'}.get(delay,'libgstpipewire-profile.so'))).read_bytes())
if delay==2000000:
 host.ssh('python3 -',input=b"from pathlib import Path;import os;p=Path('/var/lib/samurai/k262-stills');assert not p.exists();p.mkdir(mode=0o700);os.chown(p,10000,10000)")
r=host.ssh('python3 - '+str(delay),input=(R/'native-pipewire-probe.py').read_bytes(),timeout=65,check=False)
(host.PRIVATE/('probe-'+str(delay)+'-private.log')).write_bytes(r.stdout+r.stderr)
try:d=json.loads(r.stdout)
except ValueError:raise RuntimeError('Probe failed before report; inspect private log') from None
(R/('probe-'+str(delay)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
