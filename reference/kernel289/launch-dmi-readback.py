"""Submit exactly one isolated DMI readback worker on the verified kernel288 boot."""
from pathlib import Path
import base64,hashlib,json,shlex
import host

ROOT=Path(__file__).resolve().parent
proof=json.loads((ROOT/'dmi-tool-validation.json').read_text())
data=(host.PRIVATE/'dmi-readback-aarch64-private').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['binary_sha256']
assert not (host.PRIVATE/'dmi-launch-private.json').exists()
host.ssh("python3 -c \"from pathlib import Path;p=Path('/var/lib/samurai/k289-tools');p.mkdir(mode=0o700);(p/'dmi-readback.part').write_bytes(b'')\"",timeout=12)
for offset in range(0,len(data),65536):
 block=data[offset:offset+65536]
 code=f"from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k289-tools/dmi-readback.part');assert p.stat().st_size=={offset};b=sys.stdin.buffer.read();assert len(b)=={len(block)} and hashlib.sha256(b).hexdigest()=={hashlib.sha256(block).hexdigest()!r};p.open('ab').write(b)"
 host.ssh('python3 -c '+shlex.quote(code),input=block,timeout=12)
worker=(ROOT/'native-dmi-readback.py').read_bytes()
code=r'''
from pathlib import Path
import base64,hashlib,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k288-work/boot-id-private.txt').read_bytes()
p=r/'k289-tools/dmi-readback.part';target=r/'k289-tools/dmi-readback'
assert hashlib.sha256(p.read_bytes()).hexdigest()==BINARY_SHA and not target.exists();p.rename(target);target.chmod(0o700)
assert subprocess.run([str(target),'--self-test'],capture_output=True).returncode==0
script=r/'k289-tools/native-dmi-readback.py';assert not script.exists();script.write_bytes(base64.b64decode(WORKER));compile(script.read_bytes(),str(script),'exec')
assert not (r/'k289-dmi-r1').exists()
with (r/'k289-tools/dmi-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=289,pid=child.pid,start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''.replace('BINARY_SHA',repr(proof['binary_sha256'])).replace('WORKER',repr(base64.b64encode(worker).decode()))
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'dmi-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
