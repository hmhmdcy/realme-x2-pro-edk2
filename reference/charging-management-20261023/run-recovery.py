"""One explicit recovery phase; camera chat must have yielded this window."""
from pathlib import Path
import importlib.util
import json
import re
import shlex
import subprocess
import sys

ref = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('charging_window',ref/'device-window.py')
window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
host=window.host
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/recovery')
private.mkdir(exist_ok=True,mode=0o700)
expected=json.loads((ref.parent/'kernel440/current-state-validation.json').read_text())
action=sys.argv[1]

def call(code, raw=False, timeout=35, check=True):
    q=(host.raw_ssh if raw else host.ssh)('python3 -c '+shlex.quote(code),timeout=timeout,check=False)
    (private/(action+'-stdout-private.txt')).write_bytes(q.stdout)
    (private/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if check and q.returncode:
        print(q.stderr.decode(errors='replace')[-1200:])
        raise SystemExit(q.returncode)
    return q

def marker(name, data):
    with (private/name).open('x') as f: json.dump(data,f)

if action=='inspect-services':
    code="""from pathlib import Path
import json,subprocess
services={}
for n in ['samurai-ssc','iio-sensor-proxy','greetd','modemmanager','elogind']:
 try:
  q=subprocess.run(['rc-service',n,'status'],capture_output=True,text=True,timeout=2);services[n]={'exit':q.returncode,'text':(q.stdout+q.stderr).strip()}
 except subprocess.TimeoutExpired:services[n]={'status_query_timed_out':True}
processes={n:[] for n in ['phoc','phosh','pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in processes:processes[n].append({'pid':p.name,'uid':p.stat().st_uid})
 except OSError:pass
ssc=Path('/run/samurai-ssc/state.json')
print(json.dumps({'services':services,'processes':processes,'ssc':json.loads(ssc.read_text()) if ssc.exists() else None,'uptime':Path('/proc/uptime').read_text(),'taint':Path('/proc/sys/kernel/tainted').read_text(),'dmesg_tail':subprocess.check_output(['dmesg'],text=True).splitlines()[-45:]}))
"""
    q=call(code,raw=True);print(q.stdout.decode())
elif action in ['preflight','postboot']:
    code='EXPECTED='+repr(expected)+'\n'+(ref/'recovery-baseline.py').read_text()
    q=call(code,raw=action=='postboot',timeout=40);q.check_returncode()
    data=json.loads(q.stdout)
    if action=='preflight':
        assert data['taint']==512
        original=json.loads((private.parent/'window3/snapshot-stdout-private.json').read_text())
        assert data['boot_id']==original['boot_id']
    else:
        before=json.loads((private/'preflight-stdout-private.txt').read_text())
        assert data['taint']==0 and data['boot_id']!=before['boot_id']
        guard='/var/lib/samurai/charging-20261023-recovered/boot-id-private.txt'
        code='from pathlib import Path\nimport os\np=Path('+repr(guard)+');p.parent.mkdir(mode=0o700,exist_ok=True)\nwith p.open("x") as f:f.write('+repr(data['boot_id']+'\n')+');f.flush();os.fsync(f.fileno())'
        host.raw_ssh('python3 -c '+shlex.quote(code),timeout=15).check_returncode()
        (private.parent/'boot-adoption-private.json').write_text(json.dumps({'guard_path':guard,'original_key_verified':True,'baseline440_verified':True}))
        code="""from pathlib import Path
p=Path('/root/charging-management-20261023/original-private.json')
backup=p.with_name('original-before-recovery-private.json')
assert p.exists() and not backup.exists();p.rename(backup)
"""
        host.raw_ssh('python3 -c '+shlex.quote(code),timeout=15).check_returncode()
    print(json.dumps({k:v for k,v in data.items() if k not in ['boot_id','core']},indent=2))
elif action in ['quiesce','resume-quiesce']:
    assert json.loads((private/'preflight-stdout-private.txt').read_text())['taint']==512
    code="""from pathlib import Path
import subprocess,sys,json
p=Path('/var/lib/samurai/charging-20261023-quiesce-worker.py');assert not p.exists();p.write_bytes(sys.stdin.buffer.read())
with Path('/var/lib/samurai/charging-20261023-quiesce-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid}))
"""
    script='recovery-quiesce.py'
    if action=='resume-quiesce':
        script='recovery-quiesce-resume.py'
        code=code.replace('charging-20261023-quiesce-worker','charging-20261023-quiesce-resume-worker')
    marker(action+'-request.json',{'request_count':1})
    q=host.ssh('python3 -c '+shlex.quote(code),input=(ref/script).read_bytes(),timeout=20)
    (private/'quiesce-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe-quiesce':
    code="""from pathlib import Path
import json
p=Path('/var/lib/samurai/charging-20261023-recovery')
s=json.loads((p/'state-private.json').read_text())
print(json.dumps({'state':s,'summary':json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None,'failure':(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None}))
"""
    q=call(code);q.check_returncode();data=json.loads(q.stdout);print(json.dumps(data,indent=2))
    if data['state']['terminal']:
        assert data['state']['exit_code']==0
        (private/'quiesce-passed.json').write_text(json.dumps(data['summary']))
elif action in ['inspect-restart','restart']:
    assert json.loads((private/'quiesce-passed.json').read_text())['taint']==512
    code=(ref/'recovery-restart.py').read_text()
    if action=='inspect-restart': code="import sys;sys.argv=['recovery-restart.py','--inspect']\n"+code
    else:
        assert (private/'inspect-restart-stdout-private.txt').exists()
        marker('restart-request.json',{'request_count':1,'partitions_written':[]})
    q=call(code,raw=action=='restart',timeout=25,check=action!='restart')
    print(json.dumps({'phase':action,'ssh_return':q.returncode,'stdout':q.stdout.decode(errors='replace')[-1000:]}))
elif action=='finish-bootloader':
    assert (private/'restart-request.json').exists()
    fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
    q=subprocess.run([fb,'devices'],capture_output=True,timeout=15,check=True)
    found=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',q.stdout.decode())
    expected_id=json.loads((private.parent.parent/'kernel109/fastboot-identity.json').read_text())['serial']
    assert found==[expected_id]
    q=subprocess.run([fb,'-s',expected_id,'getvar','product'],capture_output=True,timeout=15,check=True)
    assert re.search(r'product:\s*msmnile\b',(q.stdout+q.stderr).decode())
    marker('fastboot-reboot-request.json',{'request_count':1,'partitions_written':[]})
    q=subprocess.run([fb,'-s',expected_id,'reboot'],capture_output=True,timeout=20,check=True)
    (private/'fastboot-reboot-private.txt').write_bytes(q.stdout+q.stderr)
    print(json.dumps({'reboot_requested_once':True,'partitions_written':[]}))
else: raise ValueError(action)
