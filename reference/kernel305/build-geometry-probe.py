from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;binary=host.PRIVATE/'sensor-geometry-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-s',str(HERE/'sensor-geometry.c'),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'geometry-probe-compile-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stderr.decode()
report=dict(stage=305,werror_compile=True,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256((HERE/'sensor-geometry.c').read_bytes()).hexdigest(),hardware_tested=False)
(HERE/'geometry-probe-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
