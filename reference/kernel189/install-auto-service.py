"""Use the reviewed service installer with a separate current-stage backup set."""
from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent;ssc=ref.parents[1]/'linux-port/ssc'
for name in ['samurai-ssc.py','samurai-ssc.initd','iio-sensor-proxy.initd','iio-sensor-proxy.conf']:
 path=ssc/name;dest='/var/lib/samurai/k189-tools/'+name;host.upload(path,dest)
 host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
code=(ref.parent/'kernel188/install-service.py').read_text().replace('k188','k189').replace('stage=188','stage=189')
try:p=host.ssh('python3 -',input=code.encode(),timeout=55)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'auto-install-failure-private.log').write_bytes(error.stdout+error.stderr);raise
(host.PRIVATE/'auto-install-host-private.log').write_bytes(p.stdout+p.stderr)
(ref/'auto-install-validation.json').write_bytes(p.stdout)
print(p.stdout.decode())
