from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in [6000010,6000011,6000012,6000014,6000015,6000016,6000017,6000018,6000019,6000020,6000022,6000023,6000024,6000025,6000026,6000027,6000028,6000029,6000030,6000031,6000032,6000033] + list(range(6000034,6000040))
if mode==6000019:
 setup="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-tools/native-stream-probe');assert not p.exists();p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/'native-stream-probe').read_bytes())
if mode==6000014:
 for local,remote in [('libpipewire-broadcast-candidate.so','/var/lib/samurai/k263-core/libpipewire-0.3.so.0'),('libspa-libcamera-broadcast-candidate.so','/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so')]:
  setup="from pathlib import Path;import sys;p=Path("+repr(remote)+");p.parent.mkdir(exist_ok=True);p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
  host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/local).read_bytes())
if mode==6000022:
 for local,remote in [('libpipewire-lease-candidate.so','/var/lib/samurai/k263-core/libpipewire-0.3.so.0'),('libspa-libcamera-lease-candidate.so','/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so')]:
  setup="from pathlib import Path;import sys;p=Path("+repr(remote)+");p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
  host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/local).read_bytes())
if mode==6000028:
 setup="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-core/libpipewire-0.3.so.0');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/'libpipewire-lease-r2-candidate.so').read_bytes())
if mode==6000034:
 for local,remote in [('libpipewire-reconfigure-candidate.so','/var/lib/samurai/k263-core/libpipewire-0.3.so.0'),('libspa-libcamera-broadcast-candidate.so','/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so')]:
  setup="from pathlib import Path;import sys;p=Path("+repr(remote)+");p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
  host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/local).read_bytes())
for name in ['advanced-runner.py','advanced-probe.py','select-front.py']:
 setup="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-tools')/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(R/name).read_bytes())
r=host.ssh('python3 - '+str(mode),input=(R/'native-advanced.py').read_bytes(),timeout=120,check=False)
(host.PRIVATE/('advanced-'+str(mode)+'-private.log')).write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/('advanced-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
