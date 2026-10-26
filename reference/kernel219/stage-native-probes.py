from pathlib import Path
import gzip,hashlib,host,json,shlex

here=Path(__file__).resolve().parent
proof=json.loads((here/'native-probe-build-validation.json').read_text())
binary=(host.PRIVATE/'native-mode-probe219').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['probe_sha256']
payload=gzip.compress(binary,mtime=0)
code="from pathlib import Path;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes();p=root/'k219-probe-stage';assert not p.exists();p.mkdir(mode=0o700);(p/'probe.gz').touch(mode=0o600)"
host.ssh('python3 -c '+shlex.quote(code),timeout=30)
for offset in range(0,len(payload),65536):
    chunk=payload[offset:offset+65536]
    code="from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k219-probe-stage/probe.gz');d=sys.stdin.buffer.read();assert len(d)=="+str(len(chunk))+" and hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(chunk).hexdigest())+";assert p.stat().st_size=="+str(offset)+";p.open('ab').write(d)"
    host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
code="from pathlib import Path;import gzip,hashlib;d=gzip.decompress(Path('/var/lib/samurai/k219-probe-stage/probe.gz').read_bytes());assert hashlib.sha256(d).hexdigest()=="+repr(proof['probe_sha256'])+";p=Path('/run/samurai-camera219-probes');assert not p.exists();p.mkdir(mode=0o755);b=p/'native-mode-probe';b.write_bytes(d);b.chmod(0o755)"
host.ssh('python3 -c '+shlex.quote(code),timeout=30)
source=(here/'native-mode-runner.py').read_bytes()
code="from pathlib import Path;import hashlib,sys;d=sys.stdin.buffer.read();assert hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(source).hexdigest())+";Path('/run/samurai-camera219-probes/mode-runner.py').write_bytes(d)"
host.ssh('python3 -c '+shlex.quote(code),input=source,timeout=30)
print('219 native capture probe and graph-restoring runner staged; no capture yet')
