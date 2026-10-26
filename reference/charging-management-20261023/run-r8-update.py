"""Launch the R8 two-file update once after handback, then fetch that same worker."""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import secrets
import time

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT = PRIVATE / 'r8-update'
TRANSACTION = 'charging-update-r8'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

LAUNCH = r'''from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
os.umask(0o077);data=json.loads(sys.stdin.buffer.read())
assert data['transaction']=='charging-update-r8'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
guard=Path(data['guard'])
assert boot==data['expected_boot']==guard.read_text().strip()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['package']['old_manifest_sha256']
base=Path('/root/charging-management-20261023/charging-update-r8-runner')
lease=Path('/run/samurai-charging-r8-window.json')
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
 'boot_id':boot,'issued_boottime_s':issued,'expires_boottime_s':issued+300}).encode())
with paths['request'].open('rb') as source,paths['log'].open('xb') as log:
 child=subprocess.Popen(['python3','-B',str(paths['worker']),'--execute-r8'],stdin=source,
  stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
receipt={'pid':child.pid,'startticks':ticks,'worker':str(paths['worker']),
 'transaction':data['transaction'],'worker_sha256':data['worker_sha256'],'boot_id':boot}
create(paths['pid'],json.dumps(receipt).encode())
print(json.dumps(receipt),flush=True)
'''

FETCH = r'''from pathlib import Path
import base64,hashlib,json,sys
request=json.loads(sys.stdin.buffer.read());assert request['transaction']=='charging-update-r8'
base=Path('/root/charging-management-20261023/charging-update-r8-runner')
receipt_path=base.with_suffix('.pid-private.json')
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
state='launch_outcome_unknown'
if receipt:
 assert receipt['worker_sha256']==request['worker_sha256'] and receipt['boot_id']==request['expected_boot']
 assert receipt['worker']==str(base.with_suffix('.py'))
 p=Path('/proc')/str(receipt['pid'])
 try:
  argv=(p/'cmdline').read_bytes().split(bytes([0]))
  fields=(p/'stat').read_text().rsplit(')',1)[1].split();ticks=fields[19]
  state=('pid_reused' if ticks!=receipt['startticks'] else
         'alive' if receipt['worker'].encode() in argv else
         'exited_zombie' if fields[0]=='Z' else 'unknown')
 except FileNotFoundError:state='absent'
 except OSError:state='unknown'
out=base.parent/request['transaction'];files={}
def retain(name,path):
 assert path.is_file() and not path.is_symlink() and path.stat().st_size<2000000
 raw=path.read_bytes();files[name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
if out.exists():
 for p in sorted(out.iterdir()):retain(p.name,p)
for name,suffix in dict(worker='.py',request='.request-private.json',pid='.pid-private.json',log='.log').items():
 p=base.with_suffix(suffix)
 if p.exists():retain('runner-'+name+'-private',p)
print(json.dumps({'process_state':state,'process':receipt,'files':files}))
'''


def local_inputs():
    directory = REF.parent / 'charging-oem-audit-20261023/r8-update'
    worker = (directory / 'update-r8.py').read_bytes()
    tested = json.loads((directory / 'test-result.json').read_bytes())
    assert tested['passed'] and tested['tested_files']['update-r8.py'] == sha(worker)
    package = json.loads((REF / 'r8-payload-result.json').read_bytes())
    payload = (PRIVATE / 'r8-candidate/thermal-bands-payload.tar.gz').read_bytes()
    assert sha(payload) == package['payload_sha256'] and len(payload) == package['payload_bytes']
    assert package['old_manifest_sha256'] == '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
    assert package['new_manifest_sha256'] == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
    adoption = json.loads((PRIVATE / 'boot-adoption-private.json').read_bytes())
    endpoint = json.loads((PRIVATE / 'r7-postboot/usb-ipv6-transport-private.json').read_bytes())
    assert adoption['original_key_verified'] and adoption['baseline440_verified']
    assert endpoint['original_key_verified']
    compile(LAUNCH, '<r8-launch>', 'exec')
    compile(FETCH, '<r8-fetch>', 'exec')
    return worker, package, payload, adoption['guard_path'], endpoint['observed_new_boot']


def run(action, confirmed=False):
    if action == 'check-local':
        worker, package, payload, guard, boot = local_inputs()
        print(json.dumps(dict(local_inputs_verified=True, worker_sha256=sha(worker),
                              payload_bytes=len(payload), phone_accessed=False)))
        return 0
    OUT.mkdir(mode=0o700, exist_ok=True)
    marker = OUT / 'launch-request-private.json'
    if action == 'launch':
        assert confirmed, 'Current explicit camera handback required'
        worker, package, payload, guard, boot = local_inputs()
        incoming = dict(transaction=TRANSACTION, worker_base64=base64.b64encode(worker).decode(),
                        worker_sha256=sha(worker), payload_base64=base64.b64encode(payload).decode(),
                        package=package, guard=guard, expected_boot=boot, token=secrets.token_hex(24))
        with marker.open('x') as stream:
            json.dump({k: v for k, v in incoming.items() if k not in ['worker_base64', 'payload_base64']}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open(OUT, os.O_DIRECTORY | os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        code = LAUNCH
    elif action == 'fetch':
        incoming = json.loads(marker.read_bytes())
        code = FETCH
    else:
        raise ValueError(action)
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    # Stream the source, avoiding the Windows command-line size limit. JSON is
    # embedded as a Python byte literal, never interpolated into shell code.
    request = json.dumps(incoming).encode()
    program = 'import io,sys\nsys.stdin=io.TextIOWrapper(io.BytesIO(' + repr(request) + '))\n' + code
    response = window.host.ssh('python3 -', input=program.encode(), timeout=35, check=False)
    stamp = str(time.time_ns())
    (OUT / (action + '-' + stamp + '-stdout-private.json')).write_bytes(response.stdout)
    (OUT / (action + '-' + stamp + '-stderr-private.txt')).write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-2200:])
        return response.returncode
    data = json.loads(response.stdout)
    if action == 'fetch':
        retained = OUT / ('fetch-' + stamp)
        retained.mkdir(mode=0o700)
        for name, entry in data['files'].items():
            assert '/' not in name and '\\' not in name
            raw = base64.b64decode(entry['base64'], validate=True)
            assert sha(raw) == entry['sha256']
            (retained / name).write_bytes(raw)
        result = json.loads((retained / 'result.json').read_bytes()) if 'result.json' in data['files'] else None
        terminal = data['process_state'] in ['absent', 'pid_reused', 'exited_zombie'] and result is not None and result.get('terminal') is True
        print(json.dumps(dict(process_state=data['process_state'], process=data['process'],
                              retained_directory=str(retained), terminal_verified=terminal,
                              result=result), indent=2))
    else:
        print(json.dumps({k: v for k, v in data.items() if k not in ['boot_id', 'transaction', 'worker']}))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check-local', 'launch', 'fetch'])
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run(args.action, args.window_confirmed))
