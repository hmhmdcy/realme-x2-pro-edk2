"""Run the complete same-condition PM test, not the unavailable pm_test interface."""
from pathlib import Path
import hashlib,subprocess
import host

ref=Path(__file__).resolve().parent
host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
data=(ref.parent/'kernel188/test-persistent-suspend.py').read_text().replace('k188','k189').replace('stage=188','stage=189')
data=data.replace('k189-reboot-runtime','k189r2-reboot-runtime')
path=ref/'test-persistent-suspend.py';assert not path.exists();path.write_text(data)
subprocess.run(['python3','-m','py_compile',str(path)],check=True)
dest='/var/lib/samurai/k189-tools/test-persistent-suspend.py';host.upload(path,dest)
host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
marker=host.PRIVATE/'persistent-pm-worker-pid-private.txt';assert not marker.exists()
p=host.ssh("test ! -e /var/lib/samurai/k189-ssc-pm && nohup sh -c 'python3 /var/lib/samurai/k189-tools/test-persistent-suspend.py; result=$?; printf \"%s\\n\" \"$result\" > /var/lib/samurai/k189-tools/pm-worker-exit.txt' > /var/lib/samurai/k189-tools/pm-worker-private.log 2>&1 < /dev/null & echo $!")
marker.write_bytes(p.stdout)
print('One full persistent-service suspend worker submitted; inspect completion before any retry.')
