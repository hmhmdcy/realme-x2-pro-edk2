from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import hashlib,json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k260-work/boot-id-private.txt').read_bytes()
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
runtime={p:Path(p,'power/runtime_status').read_text().strip() for p in devices}
procs=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['phosh','pipewire','wireplumber','snapshot','megapixels']:procs.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except OSError:pass
report=dict(stage=264,current260_boot_verified=True,plugin_sha256=hashlib.sha256(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so').read_bytes()).hexdigest(),runtime=runtime,processes=procs,taint=int(Path('/proc/sys/kernel/tainted').read_text()),gpu_fault_count=subprocess.check_output(['dmesg']).count(b'gpu fault:'))
assert report['plugin_sha256']=='d7a5500688d2881d04bc04c614eb46f00da7070bb96224c7f43f97b3a0e22935'
assert all(v=='suspended' for v in runtime.values()) and report['taint']==0
assert not any(p['name'] in ['snapshot','megapixels'] for p in procs)
print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'baseline-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(Path(__file__).parent/'baseline-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
