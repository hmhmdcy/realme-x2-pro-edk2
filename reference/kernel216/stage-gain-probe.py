from pathlib import Path
import hashlib,host,json,shlex
here=Path(__file__).resolve().parent;proof=json.loads((here/'gain-probe-build-validation.json').read_text());data=(host.PRIVATE/'raw-gain-sync-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['sha256']
for offset in range(0,len(data),65536):
    chunk=data[offset:offset+65536]
    code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k216-baseline/raw-gain-sync-probe');"+("assert not p.exists();p.touch(mode=0o600);" if offset==0 else "")+"assert p.stat().st_size=="+str(offset)+";d=sys.stdin.buffer.read();assert len(d)=="+str(len(chunk))+";p.open('ab').write(d)"
    host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
code="from pathlib import Path;import hashlib;assert hashlib.sha256(Path('/var/lib/samurai/k216-baseline/raw-gain-sync-probe').read_bytes()).hexdigest()=="+repr(proof['sha256'])
host.ssh('python3 -c '+shlex.quote(code),timeout=20);print('216 finite gain probe transferred and SHA256 verified')
