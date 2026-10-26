"""Locate the SSC accelerometer's actual udev device and standard rules."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R.parent/'kernel268/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import subprocess,json
raw=subprocess.check_output(['udevadm','info','--export-db'],text=True);found=[]
for block in raw.split('\n\n'):
 if 'ssc-accel' not in block:continue
 path=next((l[3:] for l in block.splitlines() if l.startswith('P: ')),None)
 props={l[3:].split('=',1)[0]:l.split('=',1)[1] for l in block.splitlines() if l.startswith('E: ') and any(x+'=' in l for x in ['IIO_SENSOR_PROXY_TYPE','ACCEL_MOUNT_MATRIX','SUBSYSTEM','DEVNAME'])}
 found.append(dict(path=path,properties=props))
rules={str(p):p.read_text() for directory in ['/usr/lib/udev/rules.d','/lib/udev/rules.d','/etc/udev/rules.d'] for p in Path(directory).glob('*sensor*') if p.is_file()}
print(json.dumps(dict(devices=found,rules=rules)))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=20);(P/'sensor-udev-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps(d['devices'],indent=2))
for name,s in d['rules'].items():
 print(name)
 print('\n'.join(l for l in s.splitlines() if any(x in l for x in ['ssc','fastrpc','ACCEL_MOUNT_MATRIX','modalias'])))
