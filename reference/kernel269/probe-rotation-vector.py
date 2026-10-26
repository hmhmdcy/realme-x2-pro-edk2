"""Observe one bounded stock SSC accelerometer stream and its mount matrix."""
from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R.parent/'kernel268/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
out=Path('/var/lib/samurai/k269-rotation-vector-r1');out.mkdir(mode=0o700)
before=subprocess.check_output(['dmesg']);lib=Path('/usr/lib/samurai/ssc/libssc.so.2')
assert lib.is_file();digest=hashlib.sha256(lib.read_bytes()).hexdigest()
env=dict(os.environ,LD_LIBRARY_PATH=str(lib.parent),LIBSSC_LIGHT_DATA_TYPE='wise_light',G_MESSAGES_DEBUG='all')
q=subprocess.run(['ssccli','--debug','--sensor','accelerometer','--timeout','4'],env=env,capture_output=True,timeout=18)
raw=(q.stdout+q.stderr).decode(errors='replace');(out/'ssc-debug-private.log').write_text(raw)
database=subprocess.run(['udevadm','info','--export-db'],capture_output=True,text=True,timeout=12).stdout
(out/'udev-private.txt').write_text(database)
udev=[]
for block in database.split('\n\n'):
 if 'IIO_SENSOR_PROXY_TYPE=ssc-accel' in block:
  udev.append({l[3:].split('=',1)[0]:l.split('=',1)[1] for l in block.splitlines() if l.startswith('E: ') and any(k+'=' in l for k in ['IIO_SENSOR_PROXY_TYPE','ACCEL_MOUNT_MATRIX'])})
after=subprocess.check_output(['dmesg']);faults={k:after.count(v)-before.count(v) for k,v in dict(warn=b'WARNING:',oops=b'Oops:',fatal=b'fatal error received').items()}
assert q.returncode==0 and 'Accelerometer sensor measurement:' in raw and not any(faults.values())
report=dict(stage=269,ssc_cli_exit=q.returncode,library_sha256=digest,mount_matrix_lines=[l.split('mount-matrix:',1)[1].strip() for l in raw.splitlines() if 'mount-matrix:' in l],
 measurement_lines=[l[l.index('Accelerometer sensor measurement:'):] for l in raw.splitlines() if 'Accelerometer sensor measurement:' in l][:6],
 udev_accelerometer_properties=udev,samples=raw.count('Accelerometer sensor measurement:'),fault_delta=faults,
 original_sensor_proxy_not_restarted=True,no_configuration_changed=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert run in ['r1','left-up','normal','face-up']
if run!='r1':code=code.replace('rotation-vector-r1','rotation-vector-'+run)
q=h.ssh('python3 -',input=code.encode(),timeout=40);(P/('rotation-vector-'+run+'-response-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if run!='r1':d['user_confirmed_physical_pose']=run
(R/('rotation-vector-'+run+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
