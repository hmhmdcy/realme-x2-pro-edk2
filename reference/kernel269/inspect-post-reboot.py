"""Read service identities and private log locations after the unexpected reboot."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import hashlib,json,subprocess,time
names=['pipewire','wireplumber','phosh','phoc','snapshot','iio-sensor-prox','ModemManager']
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if any(name.startswith(n) for n in names):
   processes.append(dict(pid=int(p.name),comm=name,start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except (FileNotFoundError,ProcessLookupError):pass
logs=[]
for parent in ['/var/log','/var/lib/samurai']:
 for p in Path(parent).rglob('*'):
  if p.is_file() and any(s in p.name.lower() for s in ['log','core','crash','snapshot','pipewire','wireplumber','services-current']):
   st=p.stat()
   if time.time()-st.st_mtime<10800:logs.append(dict(path=str(p),bytes=st.st_size,mtime=st.st_mtime))
configs={}
for parent in ['/usr/share/applications','/home/user/.local/share/applications','/home/samurai/.local/share/applications']:
 for p in Path(parent).glob('*Snapshot*'):
  if p.is_file():configs[str(p)]=p.read_text()
kernel=subprocess.check_output(['dmesg']).decode(errors='replace')
report=dict(processes=processes,logs=logs,configs=configs,current_dmesg=kernel,
 taint=Path('/proc/sys/kernel/tainted').read_text().strip(),uptime=float(Path('/proc/uptime').read_text().split()[0]),
 sensor_runtime={n:(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()) for n in ['7-0010','9-0010']})
print(json.dumps(report))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=25);(P/'post-reboot-observation-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps({k:v for k,v in d.items() if k not in ['current_dmesg','configs']},indent=2))
print(json.dumps(d['configs'],indent=2))
