"""Launch r6 once in an explicitly returned window, or fetch that same worker.

No service, USB, PM or device action occurs on import.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import secrets
import shlex
import sys

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
REMOTE = '/root/charging-management-20261023/charging-update-r6-runner'


def run(action, window_confirmed=False):
    out = PRIVATE / 'r6-update'
    out.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
    if action == 'launch':
        if not window_confirmed:
            raise SystemExit('Explicit camera/Bluetooth handback is required before launch')
        directory = REF.parent / 'charging-session-20261023/r6-update'
        tested = json.loads((directory / 'test-result.json').read_text())
        worker = (directory / 'update-r6.py').read_bytes()
        digest = hashlib.sha256(worker).hexdigest()
        assert tested['passed'] and tested['tested_files']['update-r6.py'] == digest
        payload = (PRIVATE / 'r6-candidate/r5-to-r6-payload.tar.gz').read_bytes()
        package = json.loads((REF / 'r6-payload-result.json').read_text())
        assert hashlib.sha256(payload).hexdigest() == package['payload_sha256']
        recovered = json.loads((PRIVATE / 'pm-r5-recovery/snapshot-private.json').read_text())
        assert recovered['result']['restored'] and recovered['result']['worker_exited']
        expected_boot = recovered['boot_id']
        token = secrets.token_hex(24)
        # Creating this local marker makes unknown launch outcomes fetch-only.
        with (out / 'launch-request-private.json').open('x') as stream:
            json.dump({'worker_sha256': digest, 'expected_boot': expected_boot,
                       'window_token': token, 'dispatch_count': 1}, stream)
        incoming = {'worker_base64': base64.b64encode(worker).decode(), 'worker_sha256': digest,
                    'payload_base64': base64.b64encode(payload).decode(), 'package': package,
                    'expected_boot': expected_boot, 'token': token}
        code = '''from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
os.umask(0o077);data=json.loads(sys.stdin.buffer.read())
base=Path('/root/charging-management-20261023/charging-update-r6-runner')
lease=Path('/run/samurai-charging-r6-window.json')
paths=[base.with_suffix(x) for x in ['.py','.request-private.json','.pid','.log']]
assert not any(p.exists() for p in paths) and not lease.exists()
assert not Path('/root/charging-management-20261023/charging-update-r6').exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
guard=Path('/var/lib/samurai/k449-adopted/boot-id-private.txt')
assert boot==data['expected_boot']==guard.read_text().strip()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['package']['old_manifest_sha256']
dt=Path('/sys/firmware/devicetree/base');compat=(dt/'compatible').read_bytes()
assert b'realme,samurai' in compat.split(bytes([0]))
serial=Path('/sys/devices/soc0/serial_number').read_bytes()
assert serial.strip()
identity={'boot_id':boot,'serial_sha256':sha(serial),'compatible_sha256':sha(compat)}
worker=base64.b64decode(data['worker_base64'],validate=True)
assert sha(worker)==data['worker_sha256']
request={'transaction':'charging-update-r6','guard':str(guard),'identity':identity,'window_token':data['token'],
 'old_manifest_sha256':data['package']['old_manifest_sha256'],'new_manifest_sha256':data['package']['new_manifest_sha256'],
 'payload_sha256':data['package']['payload_sha256'],'payload_base64':data['payload_base64']}
with paths[0].open('xb') as f:f.write(worker);f.flush();os.fsync(f.fileno())
with paths[1].open('x') as f:json.dump(request,f);f.flush();os.fsync(f.fileno())
with lease.open('x') as f:
 json.dump({'transaction':'charging-update-r6','owner':'charging','camera_released':True,
  'bluetooth_released':True,'exclusive':True,'token':data['token'],'boot_id':boot,
  'expires_boottime_s':time.clock_gettime(time.CLOCK_BOOTTIME)+300},f);f.flush();os.fsync(f.fileno())
with paths[1].open('rb') as source,paths[3].open('xb') as log:
 child=subprocess.Popen(['python3',str(paths[0]),'--execute-r6'],stdin=source,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
paths[2].write_text(str(child.pid))
print(json.dumps({'launched':True,'pid':child.pid,'worker_sha256':data['worker_sha256']}))
'''
        payload_bytes = json.dumps(incoming).encode()
    elif action == 'fetch':
        payload_bytes = None
        code = '''from pathlib import Path
import json
base=Path('/root/charging-management-20261023/charging-update-r6-runner')
pid=int(base.with_suffix('.pid').read_text());p=Path('/proc')/str(pid)/'cmdline'
try:
 argv=p.read_bytes().split(bytes([0]));state='alive' if str(base.with_suffix('.py')).encode() in argv else 'pid_reused' if any(argv) else 'unknown'
except FileNotFoundError:state='absent'
except OSError:state='unknown'
directory=Path('/root/charging-management-20261023/charging-update-r6')
files={p.name:p.read_text() for p in directory.glob('*.json')} if directory.exists() else {}
print(json.dumps({'process_state':state,'pid':pid,'files':files,'log':base.with_suffix('.log').read_text()[-12000:]}))
'''
    else:
        raise ValueError(action)
    response = window.host.ssh('python3 -c ' + shlex.quote(code), input=payload_bytes, timeout=30, check=False)
    # A fetch may be repeated against the same PID; a launch may never be repeated.
    (out / (action + '-stdout-private.json')).write_bytes(response.stdout)
    (out / (action + '-stderr-private.txt')).write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-2000:]); return response.returncode
    data = json.loads(response.stdout)
    if action == 'fetch':
        for name, raw in data['files'].items():
            assert '/' not in name and '\\' not in name
            (out / name).write_text(raw)
        result = json.loads(data['files']['result.json']) if 'result.json' in data['files'] else None
        if result is not None:
            (REF / 'r6-update-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'process_state': data['process_state'], 'result': result, 'log': data['log']}, indent=2))
    else:
        print(json.dumps(data))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch', 'fetch'])
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run(args.action, args.window_confirmed))
