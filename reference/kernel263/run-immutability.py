from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in [6000000,3000000,6000007]
setup="from pathlib import Path;import os,sys;p=Path('/var/lib/samurai/k263-tools');p.mkdir(mode=0o755,exist_ok=True);p.chmod(0o755);f=p/'pipewire-probe.py';f.write_bytes(sys.stdin.buffer.read());f.chmod(0o644)"
host.ssh('python3 -c '+shlex.quote(setup),input=(R/'immutability-probe.py').read_bytes())
binary=host.PRIVATE.parent/'kernel262/libgstpipewire-ownership.so'
setup="from pathlib import Path;import os,sys;p=Path('/var/lib/samurai/k263-candidate');p.mkdir(mode=0o755,exist_ok=True);p.chmod(0o755);f=p/'libgstpipewire.so';f.write_bytes(sys.stdin.buffer.read());f.chmod(0o644);u=Path('/var/lib/samurai/k263-user');u.mkdir(mode=0o700,exist_ok=True);os.chown(u,10000,10000)"
host.ssh('python3 -c '+shlex.quote(setup),input=binary.read_bytes())
r=host.ssh('python3 - '+str(mode),input=(R/'native-probe.py').read_bytes(),timeout=50,check=False)
(host.PRIVATE/('immutability-'+str(mode)+'-private.log')).write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/('immutability-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
