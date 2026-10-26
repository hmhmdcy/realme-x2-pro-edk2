"""Reconfigure the MC graph through an independent ordinary cam process."""
from pathlib import Path
import json
import sys
import host

which=sys.argv[1];leg=int(sys.argv[2]);assert which in ['front','rear'] and leg in [1,2,3]
code=r'''
from pathlib import Path
import json,os,pwd,re,resource,subprocess,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
services=json.loads((r/'k268-services-current-private.json').read_text())
for row in services['new_processes']:assert Path('/proc',str(row['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==row['start_ticks']
p=r/('k268-native-switch-'+str(LEG));p.mkdir(mode=0o700)
user=pwd.getpwuid(10000)
desktop=next(x for x in Path('/proc').glob('[0-9]*') if (x/'comm').exists() and (x/'comm').read_text().strip()=='phosh')
inherited={k.decode():v.decode() for item in (desktop/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
env={k:v for k,v in inherited.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
before=subprocess.check_output(['dmesg']);camera='/base/soc@0/cci@'+('ac4b000' if WHICH=='front' else 'ac4a000')+'/i2c-bus@1/camera@10'
q=subprocess.run(['cam','-c',camera,'--capture=12'],env=env,preexec_fn=demote,capture_output=True,timeout=20)
(p/'stdout-private.txt').write_bytes(q.stdout);(p/'stderr-private.txt').write_bytes(q.stderr)
sequence=[int(x) for x in re.findall(r'seq:\s*(\d+)',q.stdout.decode())]
assert q.returncode==0 and len(sequence)==12 and all(b>a for a,b in zip(sequence,sequence[1:]))
time.sleep(.5)
for n in ['7-0010','9-0010']:assert Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended'
after=subprocess.check_output(['dmesg']);faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for row in services['new_processes']:assert Path('/proc',str(row['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==row['start_ticks']
report=dict(stage=268,leg=LEG,camera=WHICH,frames=12,sequences=sequence,standard_cam_no_environment_overrides=True,
           same_pipewire_and_wireplumber=True,pm_suspended_after_capture=True,fault_delta=faults,taint=0)
(p/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('LEG',repr(leg)).replace('WHICH',repr(which))
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/('native-switch-'+str(leg)+'-private.json')).write_bytes(q.stdout)
(Path(__file__).parent/('native-switch-'+str(leg)+'-validation.json')).write_text(json.dumps(json.loads(q.stdout),indent=2)+'\n')
print(q.stdout.decode())
