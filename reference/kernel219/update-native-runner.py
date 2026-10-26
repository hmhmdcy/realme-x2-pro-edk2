from pathlib import Path
import hashlib,host,shlex

source=(Path(__file__).resolve().parent/'native-mode-runner.py').read_bytes()
code="from pathlib import Path;import hashlib,sys;assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k219-runtime/boot-id-private.txt').read_bytes();d=sys.stdin.buffer.read();assert hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(source).hexdigest())+";p=Path('/run/samurai-camera219-probes/mode-runner.py');assert p.exists();p.write_bytes(d)"
host.ssh('python3 -c '+shlex.quote(code),input=source,timeout=30)
print('Updated finite runner with live DMA exporter observation')
