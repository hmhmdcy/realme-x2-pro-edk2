"""Retain the required camera power domain in the normal sensor binding."""
from pathlib import Path
import difflib,hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270');W=Path('/home/cy122/x2pro-linux/camera270-kernel')
sensor=W/'drivers/media/i2c/s5k3m5.c'
text='\n'.join(l.rstrip() for l in sensor.read_text().splitlines())+'\n'
sensor.write_text(text);(R/'s5k3m5.c').write_text(text)
binding=W/'Documentation/devicetree/bindings/media/i2c/samsung,s5k3m5.yaml'
old='''  reset-gpios:
    description: Active low GPIO connected to RESET pad of the sensor.
    maxItems: 1
'''
new=old+'''
  power-domains:
    description: Power domain supplying the sensor clock controller.
    maxItems: 1
'''
assert binding.read_text().count(old)==1
binding.write_text(binding.read_text().replace(old,new))
(R/'samsung,s5k3m5.yaml').write_bytes(binding.read_bytes())
base=subprocess.check_output(['git','-C',str(W),'show','HEAD:drivers/media/i2c/s5k3m5.c'],text=True)
(R/'s5k3m5-standard-resources.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/s5k3m5.c',tofile='b/drivers/media/i2c/s5k3m5.c')))
lock=json.loads((R/'telephoto-source-validation.json').read_text());lock['source_sha256']=hashlib.sha256(text.encode()).hexdigest()
lock['sensor_power_domain_binding_added']=True
(R/'telephoto-source-validation.json').write_text(json.dumps(lock,indent=2)+'\n')
schema=P/'schema270.json'
q=subprocess.run(['/home/cy122/x2pro-linux/.venv-dtschema/bin/dt-mk-schema','-j','-o',str(schema),str(W/'Documentation/devicetree/bindings')],capture_output=True,timeout=90)
(P/'schema-build-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect schema compiler diagnostics'
print(json.dumps(dict(stage=270,required_sensor_power_domain_described=True,source_sha256=lock['source_sha256'],schema_generated=True,phone_unchanged=True)))
