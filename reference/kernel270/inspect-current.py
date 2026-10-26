"""Read current handset identity, camera services and crash evidence privately."""
from pathlib import Path
import importlib.util
import json
import re

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel270')
PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('transport269', HERE.parent/'kernel269/host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
code = r'''
from pathlib import Path
import hashlib,json,os,pwd,re,subprocess,time
def read(p):
 try:return Path(p).read_text(errors='replace')
 except OSError:return None
kernel=subprocess.check_output(['dmesg']).decode(errors='replace')
names=['pipewire','wireplumber','phosh','phoc','snapshot','iio-sensor-prox','ModemManager','cam','gst-launch']
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if not any(name.startswith(n) for n in names):continue
  processes.append(dict(pid=int(p.name),comm=name,start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19],
   state=(p/'status').read_text().split('State:',1)[1].splitlines()[0].strip(),
   uid=int((p/'status').read_text().split('Uid:',1)[1].split()[0]),
   cmdline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),
   fd1=os.readlink(p/'fd/1'),fd2=os.readlink(p/'fd/2')))
 except OSError:pass
u=pwd.getpwuid(10000);home=Path(u.pw_dir)
logs={}
for name in ['.local/state/samurai-phosh-session.log']:
 p=home/name
 if p.is_file():logs[str(p)]=p.read_text(errors='replace')[-50000:]
for p in processes:
 for key in ['fd1','fd2']:
  f=Path(p[key])
  if f.is_file() and not str(f).startswith('/dev/'):
   with f.open('rb') as src:src.seek(max(0,f.stat().st_size-50000));logs[str(f)]=src.read().decode(errors='replace')
old=Path('/var/lib/samurai/k269-snapshot-startup-r1/snapshot-private.log')
if old.is_file():logs[str(old)]=old.read_text(errors='replace')[-50000:]
pstores={str(p):p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()}
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=read(p/'name')
 if name and name.strip().startswith(('cam-front-','cam-rear-')):
  rails[name.strip()]={n:(read(p/n) or '').strip() for n in ['state','num_users','microvolts']}
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss']:
 q=subprocess.run(['modinfo','-n',name],capture_output=True,text=True)
 path=Path(q.stdout.strip())
 mods[name]=dict(loaded=Path('/sys/module',name).exists(),sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
report=dict(boot_id=read('/proc/sys/kernel/random/boot_id').strip(),previous_guard=read('/var/lib/samurai/k269-work/boot-id-private.txt'),
 release=os.uname().release,uptime_seconds=float(read('/proc/uptime').split()[0]),taint=int(read('/proc/sys/kernel/tainted')),
 processes=processes,logs=logs,pstores=pstores,dmesg=kernel,modules=mods,rails=rails,
 runtime={n:(read('/sys/bus/i2c/devices/'+n+'/power/runtime_status') or '').strip() for n in ['7-0010','9-0010']},
 remoteprocs={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
 service_manifest=read('/var/lib/samurai/k269-services-current-private.json'),
 camera_config=read('/etc/libcamera/configuration.yaml'),
 connectors={p.name:{n:(read(p/n) or '').strip() for n in ['status','enabled','dpms']} for p in Path('/sys/class/drm').glob('card*-DSI-*')})
print(json.dumps(report))
'''
q=host.transport.raw_ssh('python3 -', input=code.encode(), timeout=35)
data=json.loads(q.stdout)
(PRIVATE/'current-inspection-private.json').write_bytes(q.stdout)
faults={k:data['dmesg'].count(v) for k,v in dict(warning='WARNING:',oops='Oops:',modem='crash detected in modem',fatal='fatal error received',gpu='gpu fault:').items()}
summary={k:data[k] for k in ['release','uptime_seconds','taint','modules','rails','runtime','remoteprocs','connectors']}
summary.update(same_boot_as269=data['boot_id']==(data['previous_guard'] or '').strip(),
 processes=[{k:p[k] for k in ['pid','comm','start_ticks','state','uid']} for p in data['processes']],faults=faults,
 log_sizes={p:len(v) for p,v in data['logs'].items()},pstore_bytes={p:len(v.encode()) for p,v in data['pstores'].items()})
(HERE/'current-inspection-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
for path,log in data['logs'].items():
 if 'snapshot-startup' in path:
  lines=[l for l in log.splitlines() if re.search(r'error|warn|fail|camera|pipewire|portal|aperture',l,re.I)]
  print('Previous launch diagnostic:', '\n'.join(lines)[-7000:])
