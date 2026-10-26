"""Read actual sensor binding and camera enumeration after the controlled boot."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,struct,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def note(p):
 b=Path(p).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss','v4l2_cci','s5k3m5']:
 q=subprocess.run(['modinfo','-n',name],capture_output=True,text=True);p=Path(q.stdout.strip());loaded=Path('/sys/module',name).exists()
 mods[name]=dict(loaded=loaded,file_sha256=sha(p) if p.is_file() else None,
  loaded_note_matches_disk=loaded and (Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p)))
sensors={}
for p in Path('/sys/class/video4linux').glob('v4l-subdev*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('imx319 ','imx471 ','s5k3m5 ')):
  dev=(p/'device').resolve();sensors[name]=dict(node='/dev/'+p.name,driver=(dev/'driver').resolve().name if (dev/'driver').exists() else None,
   compatible=(dev/'of_node/compatible').read_bytes().decode().rstrip('\0'),runtime=(dev/'power/runtime_status').read_text().strip())
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-front-','cam-rear-','cam-tele-')):rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
kernel=subprocess.check_output(['dmesg']);u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name)
q=subprocess.run(['cam','--list'],env=env,preexec_fn=demote,capture_output=True,timeout=20)
print(json.dumps(dict(stage=270,modules=mods,sensors=sensors,rails=rails,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
 dmesg=kernel.decode(errors='replace'),cam_list_exit=q.returncode,cam_list=q.stdout.decode(errors='replace'),cam_stderr=q.stderr.decode(errors='replace'),
 telephoto_i2c_exists=Path('/sys/bus/i2c/devices/8-002d').exists(),
 telephoto_i2c_driver=Path('/sys/bus/i2c/devices/8-002d/driver').resolve().name if Path('/sys/bus/i2c/devices/8-002d/driver').exists() else None,
 remoteprocs={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')})))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'postboot-hardware-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
summary={k:v for k,v in d.items() if k not in ['dmesg','cam_list','cam_stderr']}
summary['cam_list']=d['cam_list']
(R/'postboot-hardware-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
print('\n'.join(l for l in d['dmesg'].splitlines() if any(k in l.lower() for k in ['s5k3m5','failed to find sensor','deferred probe','probe with driver s5k'])))
