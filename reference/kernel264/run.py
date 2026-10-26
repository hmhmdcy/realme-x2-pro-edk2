from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in range(6000041,6000067)
if mode==6000041:
 setup=r'''
from pathlib import Path
import os,pwd
root=Path('/var/lib/samurai');user=pwd.getpwuid(10000)
for name in ['k264-tools','k264-user']:
 p=root/name;assert not p.exists();p.mkdir(mode=0o755 if name.endswith('tools') else 0o700)
 if name.endswith('user'):os.chown(p,user.pw_uid,user.pw_gid)
base=Path('/usr/lib/spa-0.2');out=root/'k264-spa';assert not out.exists();out.mkdir(mode=0o755)
for p in base.iterdir():
 if p.name!='libcamera':(out/p.name).symlink_to(p,target_is_directory=p.is_dir())
(out/'libcamera').mkdir();(root/'k264-core').mkdir()
'''
 host.ssh('python3 -',input=setup.encode())
 for local,remote in [('libpipewire-source-only-candidate.so','k264-core/libpipewire-0.3.so.0'),('libspa-libcamera-broadcast-candidate.so','k264-spa/libcamera/libspa-libcamera.so')]:
  code="from pathlib import Path;import sys;p=Path('/var/lib/samurai')/"+repr(remote)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
  host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/local).read_bytes())
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE.parent/'kernel263/native-stream-probe').read_bytes())
if mode==6000047:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-core/libpipewire-0.3.so.0');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'libpipewire-proxy-only-candidate.so').read_bytes())
if mode==6000050:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'native-stream-probe').read_bytes())
if mode==6000053:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'native-diagnostic-probe').read_bytes())
if mode in [6000054,6000056]:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools/native-stream-probe');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'native-linear-probe').read_bytes())
if mode==6000055:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-spa/libcamera/libspa-libcamera.so');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'libspa-libcamera-reset-output.so').read_bytes())
if mode==6000057:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-core/libpipewire-0.3.so.0');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(host.PRIVATE/'libpipewire-binding-reset.so').read_bytes())
snapshot=host.PRIVATE/('inputs-'+str(mode));assert not snapshot.exists();snapshot.mkdir()
for name in ['advanced-runner.py','advanced-probe.py','select-front.py','pipewire264.conf','wireplumber264-off.conf','native-advanced.py']:(snapshot/name).write_bytes((R/name).read_bytes())
for name in ['advanced-runner.py','advanced-probe.py','select-front.py','pipewire264.conf','wireplumber264-off.conf']:
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k264-tools')/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=(R/name).read_bytes())
r=host.ssh('python3 - '+str(mode),input=(snapshot/'native-advanced.py').read_bytes(),timeout=120,check=False)
(host.PRIVATE/('run-'+str(mode)+'-private.log')).write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/('run-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
