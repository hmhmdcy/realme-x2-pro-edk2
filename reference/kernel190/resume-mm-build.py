from pathlib import Path
import host,subprocess
ref=Path(__file__).resolve().parent
text=(ref/'build-mm.py').read_text()
code='''from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077)
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
source=next((out/'source').iterdir());patched=(source/'src/mm-shared-qmi.c').read_bytes()
db=Path('/lib/apk/db/installed').read_bytes()
'''+text[text.index('gccdir='):]
code=code.replace("'configure')","'configure-resume')").replace("'compile')","'compile-resume')")
(ref/'resume-mm-build-expanded.py').write_text(code)
try:p=host.ssh('python3 -',input=code.encode(),timeout=1800)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'resume-mm-build-failure-private.log').write_bytes(e.stdout+e.stderr);raise SystemExit('Build failed; private logs retained')
(host.PRIVATE/'resume-mm-build-host-private.log').write_bytes(p.stdout+p.stderr);print(p.stdout.decode()[-1500:])
