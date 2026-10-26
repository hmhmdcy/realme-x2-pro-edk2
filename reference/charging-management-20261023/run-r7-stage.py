"""One R7 disk-only stage in the explicitly returned device window."""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import secrets
import shlex

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT = PRIVATE / 'r7-stage'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

LAUNCH = r'''from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
os.umask(0o077); data=json.loads(sys.stdin.buffer.read())
sha=lambda raw:hashlib.sha256(raw).hexdigest()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
guard=Path('/var/lib/samurai/k449-adopted/boot-id-private.txt')
assert boot==data['expected_boot']==guard.read_text().strip()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['package']['old_manifest_sha256']
base=Path('/root/charging-management-20261023')/(data['transaction']+'-runner')
lease=Path('/run/samurai-charging-source-stage-r7-window.json')
paths={n:base.with_suffix(s) for n,s in dict(worker='.py',request='.request-private.json',pid='.pid-private.json',log='.log').items()}
assert not any(p.exists() for p in paths.values()) and not lease.exists()
assert not (base.parent/data['transaction']).exists()
compat=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
serial=Path('/sys/devices/soc0/serial_number').read_bytes()
assert b'realme,samurai' in compat.split(bytes([0])) and serial.strip()
worker=base64.b64decode(data['worker_base64'],validate=True)
assert sha(worker)==data['worker_sha256']
request={'transaction':data['transaction'],'guard':str(guard),
 'identity':{'boot_id':boot,'serial_sha256':sha(serial),'compatible_sha256':sha(compat)},
 'window_token':data['token'],'old_manifest_sha256':data['package']['old_manifest_sha256'],
 'new_manifest_sha256':data['package']['new_manifest_sha256'],
 'payload_sha256':data['package']['payload_sha256'],'payload_base64':data['payload_base64']}
def create(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
create(paths['worker'],worker)
create(paths['request'],json.dumps(request).encode())
issued=time.clock_gettime(time.CLOCK_BOOTTIME)
create(lease,json.dumps({'transaction':data['transaction'],'owner':'charging',
 'camera_released':True,'bluetooth_released':True,'exclusive':True,'token':data['token'],
 'boot_id':boot,'issued_boottime_s':issued,'expires_boottime_s':issued+120}).encode())
with paths['request'].open('rb') as source,paths['log'].open('xb') as log:
 child=subprocess.Popen(['python3','-B',str(paths['worker']),'--execute-r7-stage'],stdin=source,
  stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
receipt={'pid':child.pid,'startticks':ticks,'worker':str(paths['worker']),
 'transaction':data['transaction'],'worker_sha256':data['worker_sha256']}
create(paths['pid'],json.dumps(receipt).encode())
print(json.dumps(receipt),flush=True)
'''

FETCH = r'''from pathlib import Path
import base64,hashlib,json,sys
request=json.loads(sys.stdin.buffer.read());tx=request['transaction']
base=Path('/root/charging-management-20261023')/(tx+'-runner')
receipt_path=base.with_suffix('.pid-private.json')
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
state='launch_outcome_unknown'
if receipt:
 p=Path('/proc')/str(receipt['pid'])
 try:
  argv=(p/'cmdline').read_bytes().split(bytes([0]))
  ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]
  state='alive' if ticks==receipt['startticks'] and receipt['worker'].encode() in argv else 'pid_reused'
 except FileNotFoundError:state='absent'
 except OSError:state='unknown'
out=base.parent/tx;files={}
if out.exists():
 for p in sorted(out.iterdir()):
  assert p.is_file() and not p.is_symlink() and p.stat().st_size<2000000
  raw=p.read_bytes();files[p.name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
log=base.with_suffix('.log')
print(json.dumps({'process_state':state,'process':receipt,'files':files,
 'log':log.read_text()[-12000:] if log.exists() else None}))
'''


def run(action, confirmed):
    OUT.mkdir(mode=0o700, exist_ok=True)
    spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
    marker=OUT/'launch-request-private.json'
    if action=='launch':
        assert confirmed, 'Current explicit camera/Bluetooth handback required'
        directory=REF.parent/'charging-session-20261023/source-stage-r7'
        worker=(directory/'stage-r7.py').read_bytes()
        tested=json.loads((directory/'test-result.json').read_text())
        assert tested['passed'] and tested['worker_sha256']==sha(worker)
        package=json.loads((REF/'r7-payload-result.json').read_text())
        payload=(PRIVATE/'r7-candidate/source-float-payload.tar.gz').read_bytes()
        assert sha(payload)==package['payload_sha256'] and len(payload)==package['payload_bytes']
        expected_boot=json.loads((PRIVATE/'r6-replug-source/bluetooth-safe-inhibit-handoff-private.json').read_text())['state']['boot_id']
        token=secrets.token_hex(24);tx='source-stage-r7-'+secrets.token_hex(8)
        incoming={'transaction':tx,'worker_base64':base64.b64encode(worker).decode(),
                  'worker_sha256':sha(worker),'payload_base64':base64.b64encode(payload).decode(),
                  'package':package,'expected_boot':expected_boot,'token':token}
        with marker.open('x') as f:
            json.dump({k:v for k,v in incoming.items() if k not in ['worker_base64','payload_base64']},f)
            f.flush();os.fsync(f.fileno())
        fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        (OUT/'worker.py').write_bytes(worker)
        code=LAUNCH
    else:
        incoming=json.loads(marker.read_text());code=FETCH
    q=window.host.ssh('python3 -c '+shlex.quote(code),input=json.dumps(incoming).encode(),timeout=35,check=False)
    (OUT/(action+'-stdout-private.json')).write_bytes(q.stdout)
    (OUT/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-2200:]);return q.returncode
    data=json.loads(q.stdout)
    if action=='fetch':
        for name,entry in data['files'].items():
            assert '/' not in name and '\\' not in name
            raw=base64.b64decode(entry['base64'],validate=True);assert sha(raw)==entry['sha256']
            (OUT/name).write_bytes(raw)
        result=json.loads((OUT/'result.json').read_text()) if 'result.json' in data['files'] else None
        if result is not None:
            (REF/'r7-stage-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'process_state':data['process_state'],'result':result,'log':data['log']},indent=2))
    else: print(json.dumps({k:v for k,v in data.items() if k not in ['transaction','worker']},indent=2))
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['launch','fetch'])
    p.add_argument('--window-confirmed',action='store_true');args=p.parse_args()
    raise SystemExit(run(args.action,args.window_confirmed))
