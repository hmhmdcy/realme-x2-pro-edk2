from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in list(range(6000070,6000075))+list(range(6000080,6000085))
worker='native-system-natural.py' if mode>=6000080 else 'native-system.py'
snapshot=host.PRIVATE/('inputs-'+str(mode));assert not snapshot.exists();snapshot.mkdir()
for name in ['system-runner.py','system-photo-probe.py','advanced-probe.py','select-front.py',worker]:
 data=(R/name).read_bytes();(snapshot/name).write_bytes(data)
 if name==worker:continue
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools')/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=data)
r=host.ssh('python3 - '+str(mode),input=(snapshot/worker).read_bytes(),timeout=120,check=False);(host.PRIVATE/('system-'+str(mode)+'-private.log')).write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/('system-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
