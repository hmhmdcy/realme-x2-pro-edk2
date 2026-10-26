from pathlib import Path
import hashlib
import host

path=Path(__file__).resolve().parent/'test-freezer-case.py'
host.ssh('test ! -e /var/lib/samurai/k189-freezer-original/userspace && cat > /var/lib/samurai/k189-tools/test-freezer-case.py.corrected',input=path.read_bytes())
digest=hashlib.sha256(path.read_bytes()).hexdigest()
host.ssh('sha256sum -c -',input=(digest+'  /var/lib/samurai/k189-tools/test-freezer-case.py.corrected\n').encode())
host.ssh('test ! -e /var/lib/samurai/k189-freezer-original/userspace && mv /var/lib/samurai/k189-tools/test-freezer-case.py.corrected /var/lib/samurai/k189-tools/test-freezer-case.py')
print('Corrected debug-site selector before the case was launched; no DSP transition repeated.')
