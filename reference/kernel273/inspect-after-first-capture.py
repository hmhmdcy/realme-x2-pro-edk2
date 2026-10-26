from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k273-main-capture-r1')
report=dict(capture_logs={n:(root/n).read_text(errors='replace') for n in ['raw-stdout-private.log','raw-stderr-private.log','rgb-stdout-private.log','rgb-stderr-private.log']},
 services={str(p):p.read_text(errors='replace') for p in [Path('/etc/init.d/samurai-ssc'),Path('/etc/conf.d/greetd'),Path('/etc/init.d/iio-sensor-proxy')]},
 levels={name:[p.parent.name for p in Path('/etc/runlevels').glob('*/'+name)] for name in ['greetd','samurai-ssc','iio-sensor-proxy']})
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'first-capture-and-service-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
for kind in ['raw','rgb']:
 text=d['capture_logs'][kind+'-stdout-private.log'];print(kind,'\n'+'\n'.join(text.splitlines()[:5]+text.splitlines()[-4:]))
 err=d['capture_logs'][kind+'-stderr-private.log'];print(kind,'diagnostic lines','\n'.join(l for l in err.splitlines() if any(w in l for w in ['WARN','ERROR','Selected sensor format','configuring streams'])))
print('runlevels',d['levels']);print(d['services']['/etc/init.d/samurai-ssc']);print(d['services']['/etc/conf.d/greetd'])
