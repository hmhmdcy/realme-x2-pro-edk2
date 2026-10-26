from pathlib import Path
import hashlib
import host

ref=Path(__file__).resolve().parent
path=ref/'test-persistent-suspend.py'
dest='/var/lib/samurai/k188-tools/test-persistent-suspend.py'
host.upload(path,dest)
host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
marker=host.PRIVATE/'suspend-worker-pid-private.txt'
assert not marker.exists()
p=host.ssh("test ! -e /var/lib/samurai/k188-ssc-pm && nohup sh -c 'python3 /var/lib/samurai/k188-tools/test-persistent-suspend.py; result=$?; printf \"%s\\n\" \"$result\" > /var/lib/samurai/k188-tools/pm-worker-exit.txt' > /var/lib/samurai/k188-tools/pm-worker-private.log 2>&1 < /dev/null & echo $!")
marker.write_bytes(p.stdout)
print('One persistent SSC suspend worker submitted; inspect completion before any further transition.')
