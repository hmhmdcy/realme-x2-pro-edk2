"""Inspect the standard service and board identity before a scoped metadata fix."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R.parent/'kernel268/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,subprocess
p=Path('/sys/firmware/devicetree/base/compatible')
result=dict(compatible=p.read_bytes().decode().strip('\0').split('\0'),
 service=Path('/etc/init.d/iio-sensor-proxy').read_text(),
 config=Path('/etc/conf.d/iio-sensor-proxy').read_text(),
 status=subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True,text=True).stdout,
 existing_rule=Path('/etc/udev/rules.d/99-realme-rmx1931-sensors.rules').exists())
print(json.dumps(result))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=20);(P/'rotation-service-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps(d,indent=2))
