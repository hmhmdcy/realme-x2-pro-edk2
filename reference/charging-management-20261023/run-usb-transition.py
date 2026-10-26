"""One guarded phase of charging DT switch; no blind retries."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
p=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-transition')
lock=json.loads((p/'transition-lock.json').read_text());action=sys.argv[1]

def query(code,raw=False,timeout=30):
    q=(w.host.raw_ssh if raw else w.host.ssh)('python3 -c '+shlex.quote(code),timeout=timeout,check=False)
    (p/(action+'-stdout-private.json')).write_bytes(q.stdout);(p/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

def once(name,data):
    with (p/name).open('x') as f:json.dump(data,f)

if action=='preflight':
    expected=json.loads((ref.parent/'kernel440/current-state-validation.json').read_text())
    code='EXPECTED='+repr(expected)+'\n'+(ref/'recovery-baseline.py').read_text()
    # The baseline checker prints one JSON object; append a separate metadata
    # pass here only after it has proved taint0/formal440 and idle resources.
    data=query(code);assert data['taint']==0
    (p/'preflight-camera-private.json').write_text(json.dumps(data))
    code="""from pathlib import Path
import hashlib,json
p=Path('/dev/disk/by-partlabel/boot')
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert Path('/etc/runlevels/default/samurai-charging').is_symlink()
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name=='mp2650'
print(json.dumps({'boot_sha256':digest,'service_boot_enabled':True,'original_observer':True,'taint':int(Path('/proc/sys/kernel/tainted').read_text())}))
"""
    data=query(code);assert data['boot_sha256']==lock['build']['rollback_boot_sha256'] and data['taint']==0
    (p/'preflight-passed.json').write_text(json.dumps(data));print(json.dumps(data))
elif action=='quiesce':
    assert (p/'preflight-passed.json').exists()
    code="""from pathlib import Path
import subprocess,sys,json
p=Path('/var/lib/samurai/charging-usb-quiesce-worker.py');assert not p.exists();p.write_bytes(sys.stdin.buffer.read())
with Path('/var/lib/samurai/charging-usb-quiesce-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid}))
"""
    once('quiesce-request.json',{'request_count':1})
    q=w.host.ssh('python3 -c '+shlex.quote(code),input=(ref/'usb-quiesce.py').read_bytes(),timeout=20)
    (p/'quiesce-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe-quiesce':
    code="""from pathlib import Path
import json
p=Path('/var/lib/samurai/charging-20261023-usb-transition')
print(json.dumps({'state':json.loads((p/'state-private.json').read_text()),'summary':json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None,'failure':(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None}))
"""
    data=query(code);print(json.dumps(data,indent=2))
    if data['state']['terminal']:
        assert data['state']['exit_code']==0 and data['summary']['taint']==0
        (p/'quiesce-passed.json').write_text(json.dumps(data['summary']))
elif action in ['inspect-restart','restart']:
    assert (p/'quiesce-passed.json').exists()
    code=(ref/'usb-restart.py').read_text()
    if action=='inspect-restart':
        code="import sys;sys.argv=['usb-restart.py','--inspect']\n"+code
        print(json.dumps(query(code)))
    else:
        assert (p/'inspect-restart-stdout-private.json').exists();once('restart-request.json',{'count':1})
        q=w.host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25,check=False)
        (p/'restart-private.txt').write_bytes(q.stdout+q.stderr);print(json.dumps({'restart_requested_once':True,'ssh_return':q.returncode}))
elif action=='flash':
    assert (p/'restart-request.json').exists()
    fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
    serial=json.loads((p.parent.parent/'kernel109/fastboot-identity.json').read_text())['serial']
    def fbcall(args,label,timeout=25):
        q=subprocess.run([fb,*args],capture_output=True,timeout=timeout)
        (p/(label+'-private.txt')).write_bytes(q.stdout+q.stderr)
        assert q.returncode==0,label
        return (q.stdout+q.stderr).decode()
    found=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',fbcall(['devices'],'fastboot-devices'))
    assert found==[serial]
    assert re.search(r'product:\s*msmnile\b',fbcall(['-s',serial,'getvar','product'],'fastboot-product'))
    for part,size in [('boot',100663296),('logdump',67108864)]:
        text=fbcall(['-s',serial,'getvar','partition-size:'+part],'fastboot-size-'+part)
        m=re.search(r'partition-size:'+part+r':\s*(0x[0-9a-fA-F]+)',text);assert m and int(m[1],16)==size
    for name in ['candidate','rollback']:
        image=Path(lock['files'][name]);digest=lock['build']['boot_sha256' if name=='candidate' else 'rollback_boot_sha256']
        assert image.stat().st_size==100663296 and hashlib.sha256(image.read_bytes()).hexdigest()==digest
    once('flash-request.json',{'partitions':['boot'],'candidate_sha256':lock['build']['boot_sha256']})
    image=Path(lock['files']['candidate']);win='E:/'+str(image)[len('/mnt/e/'):]
    text=fbcall(['-s',serial,'flash','boot',win],'flash-boot',50)
    assert re.search(r"Writing 'boot'\s+OKAY",text) and 'FAILED' not in text
    report={'boot_flash_success':True,'boot_sha256':lock['build']['boot_sha256'],'partitions_flashed':['boot'],'runtime_readback_pending':True}
    (ref/'usb-flash-result.json').write_text(json.dumps(report,indent=2)+'\n')
    once('fastboot-reboot-request.json',{'count':1});fbcall(['-s',serial,'reboot'],'fastboot-reboot')
    print(json.dumps(report))
else:raise ValueError(action)
