"""Stage one reviewed USB500 worker, or fetch that same transaction.

The Windows coordinator must own the live reader handle and supply its fresh
gate. Import is inert; launch is never retried after an unknown SSH outcome.
"""
from pathlib import Path
import argparse
import base64
import datetime as dt
import hashlib
import importlib.util
import json
import re
import shlex
import time

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
TX = 'usb500-r6-diagnostic-v1'
PREFIX = '/root/charging-management-20261023/' + TX + '-'
MANIFEST = '944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'
DECODER = '9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716'
COLLECTOR = '31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5'
REVIEWED = {'worker.py':'b9f7cc4c741ca85608ec769640b920e0783d76e383ad0c36c7c8e3c912e81f21',
            'r6-base.py':'b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98',
            'health.py':'a41942f21773c97b22d0b3760b1e256650f8e5506ee6cd0883db7145a39f4b4f',
            'test-result.json':'faf128cf133e0c91127d1d7cef466a402abdc23c93f02d46d1a9bc5910d42348'}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def validate_gate(gate, nonce, now):
    if not re.fullmatch('[a-f0-9]{48}', nonce): raise ValueError('new 24-byte nonce required')
    stamp=dt.datetime.fromisoformat(gate['host_trigger_utc'])
    if stamp.utcoffset() is None: raise ValueError('explicit host UTC offset required')
    when = stamp.timestamp()
    if not 0 <= now - when <= 5: raise ValueError('host reader gate older than five seconds')
    ready = gate['host_ready']
    if not (gate.get('owned_handle_checked') is True and ready['armed'] is True
            and type(ready['host_worker_pid']) is int and ready['host_worker_pid'] > 0
            and type(ready['target_port']) is int and 1 <= ready['target_port'] <= 15
            and ready['remaining_seconds_at_trigger'] >= 110
            and ready['capture_id'] == 'usb500-r6-' + nonce
            and ready['decoder_sha256'] == DECODER and ready['collector_sha256'] == COLLECTOR):
        raise ValueError('actual owned reader/remaining time/identity is unproved')
    stamp=dt.datetime.fromisoformat(ready['ready_at_utc'])
    if stamp.utcoffset() is None: raise ValueError('explicit sweep UTC offset required')
    ready_at = stamp.timestamp()
    if not 0 <= when - ready_at <= 3: raise ValueError('last complete armed sweep is stale')


def transport():
    source = HERE.parents[1] / 'charging-management-20261023/device-window.py'
    spec = importlib.util.spec_from_file_location('usb500_window', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.host.ssh


def validate_receipt(receipt, nonce, allow_missing=False):
    if not receipt and allow_missing:return
    expected=['python3','-B',PREFIX+nonce+'/worker.py','--worker',PREFIX+nonce]
    if not (type(receipt.get('pid')) is int and receipt['pid']>0 and type(receipt.get('start_ticks')) is int and receipt['start_ticks']>0
            and receipt.get('argv')==expected and receipt.get('worker_sha256')==REVIEWED['worker.py']):
        raise ValueError('process receipt identity differs')


REMOTE_LAUNCH = r'''from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
data=json.loads(sys.stdin.buffer.read());os.umask(0o077);assert os.geteuid()==0 and not sys.flags.optimize
root=Path(data['remote']);assert str(root)=='/root/charging-management-20261023/usb500-r6-diagnostic-v1-'+data['nonce']
guard=Path('/var/lib/samurai/k449-adopted/boot-id-private.txt')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==data['expected_boot']==guard.read_text().strip()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['manifest_sha256']
lease=Path('/run/samurai-usb500-r6-window.json');assert not lease.exists()
old=[b'/root/charging-management-20261023/charging-pm-r5.py',b'/root/charging-management-20261023/usb-reenumerate/worker.py',b'/root/charging-management-20261023/usb-power500/worker.py',b'/root/charging-management-20261023/usb-hotplug-r4/worker.py',b'/root/charging-management-20261023/charging-update-r6-runner.py',b'/root/charging-management-20261023/r6-smoke-runner.py']
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:args=p.read_bytes().split(bytes([0]))
 except FileNotFoundError:continue
 assert not any(a in old or a.startswith(b'/root/charging-management-20261023/usb500-r6-diagnostic-v1-') and a.endswith(b'/worker.py') for a in args),'prior worker still live'
root.mkdir(mode=0o700)
for name,item in data['files'].items():
 assert name in ['worker.py','r6-base.py','health.py','test-result.json']
 raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256']
 with (root/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert {n:sha((root/n).read_bytes()) for n in data['reviewed']}==data['reviewed']
tested=json.loads((root/'test-result.json').read_bytes());assert tested['passed'] is True and tested['cases']==51
assert all(tested['tested_files'][n]==data['files'][n]['sha256'] for n in ['worker.py','r6-base.py','health.py'])
serial=Path('/sys/devices/soc0/serial_number').read_bytes();assert serial.strip()
compat=Path('/sys/firmware/devicetree/base/compatible').read_bytes();assert b'realme,samurai' in compat.split(bytes([0]))
ready=dict(data['gate']['host_ready']);ready['armed_utc']=ready['ready_at_utc']
config={'transaction':'usb500-r6-diagnostic-v1','guard':str(guard),'manifest_sha256':data['manifest_sha256'],
 'identity':{'boot_id':boot,'serial_sha256':sha(serial),'compatible_sha256':sha(compat)},
 'window_token':data['token'],'host_trigger_nonce':data['nonce'],'host_ready':ready,
 'host_trigger_utc':data['gate']['host_trigger_utc'],'worker_sha256':data['files']['worker.py']['sha256']}
def save(path,obj):
 with path.open('x') as f:json.dump(obj,f);f.flush();os.fsync(f.fileno())
save(root/'config-private.json',config)
save(lease,{'transaction':'usb500-r6-diagnostic-v1','owner':'charging','camera_released':True,'bluetooth_released':True,
 'exclusive':True,'token':data['token'],'host_trigger_nonce':data['nonce'],'boot_id':boot,'expires_boottime_s':time.clock_gettime(time.CLOCK_BOOTTIME)+180})
argv=['python3','-B',str(root/'worker.py'),'--worker',str(root)]
with (root/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
stat=Path('/proc',str(child.pid),'stat').read_text();ticks=int(stat[stat.rindex(')')+2:].split()[19])
receipt={'pid':child.pid,'start_ticks':ticks,'argv':argv,'worker_sha256':data['files']['worker.py']['sha256']}
save(root/'launch-receipt-private.json',receipt)
print(json.dumps({'launched':True,'receipt':receipt,'remote_clock':{'real':time.time(),'mono':time.monotonic(),'boot':time.clock_gettime(time.CLOCK_BOOTTIME)}}),flush=True)
'''

REMOTE_FETCH = r'''from pathlib import Path
import base64,hashlib,json,sys,time
data=json.loads(sys.stdin.buffer.read());root=Path(data['remote'])
receipt=json.loads((root/'launch-receipt-private.json').read_bytes()) if (root/'launch-receipt-private.json').exists() else {}
state='unknown';pid=receipt.get('pid')
if pid:
 try:
  p=Path('/proc',str(pid));stat=(p/'stat').read_text();fields=stat[stat.rindex(')')+2:].split()
  args=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
  state='pid_reused' if int(fields[19])!=receipt['start_ticks'] else 'zombie' if fields[0]=='Z' else 'alive' if args==receipt['argv'] else 'unknown'
 except FileNotFoundError:state='absent'
files={}
if root.exists():
 for path in root.iterdir():
  if path.is_dir() and not path.is_symlink() and path.name=='__pycache__':continue
  assert path.is_file() and not path.is_symlink()
  raw=path.read_bytes();assert len(raw)<=16*1024*1024
  files[path.name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
print(json.dumps({'process_state':state,'receipt':receipt,'files':files,'remote_clock':{'real':time.time(),'mono':time.monotonic(),'boot':time.clock_gettime(time.CLOCK_BOOTTIME)}}))
'''


def run(action, nonce, gate_file=None, confirmed=False, *, ssh=None, private=PRIVATE):
    if not re.fullmatch('[a-f0-9]{48}', nonce): raise ValueError('invalid transaction nonce')
    out = private / ('usb500-r6-' + nonce)
    if action == 'launch':
        if not confirmed: raise ValueError('explicit camera/Bluetooth handback required')
        gate = json.loads(Path(gate_file).read_bytes()); validate_gate(gate, nonce, time.time())
        candidate = HERE / 'device-candidate'; tested = json.loads((candidate/'test-result.json').read_bytes())
        if tested['passed'] is not True or tested['cases'] != 51: raise ValueError('unqualified device candidate')
        files = {}
        for name in ['worker.py','r6-base.py','health.py','test-result.json']:
            raw=(candidate/name).read_bytes(); digest=sha(raw)
            if digest!=REVIEWED[name]:raise ValueError('different reviewed candidate/51-case receipt')
            if name!='test-result.json' and digest!=tested['tested_files'][name]: raise ValueError('untested candidate bytes')
            files[name]={'sha256':digest,'base64':base64.b64encode(raw).decode()}
        before=json.loads((private/'r6-update/handoff-private.json').read_bytes())
        if before['manifest_sha256']!=MANIFEST: raise ValueError('expected deployed r6 baseline')
        import secrets
        request={'nonce':nonce,'remote':PREFIX+nonce,'expected_boot':before['observation']['state']['boot_id'],
                 'manifest_sha256':MANIFEST,'token':secrets.token_hex(24),'gate':gate,'files':files,'dispatch_count':1,'reviewed':REVIEWED}
        out.mkdir(mode=0o700,exist_ok=True)
        with (out/'launch-request-private.json').open('x') as stream:
            json.dump(request,stream);stream.flush()
            import os
            os.fsync(stream.fileno())  # durable before any SSH dispatch
        code=REMOTE_LAUNCH
    elif action == 'fetch':
        request=json.loads((out/'launch-request-private.json').read_bytes());code=REMOTE_FETCH
        if request['remote']!=PREFIX+nonce or request['nonce']!=nonce or request['dispatch_count']!=1 or request['reviewed']!=REVIEWED:raise ValueError('retained identity differs')
    else:raise ValueError('unknown action')
    start=time.time()
    try:
        response=(ssh or transport())('python3 -c '+shlex.quote(code),input=json.dumps(request).encode(),timeout=30,check=False)
    except Exception as error:
        (out/(action+'-'+str(time.time_ns())+'-unknown-private.json')).write_text(json.dumps({'nonce':nonce,'action':action,'error':type(error).__name__,'fetch_only':True}))
        raise
    end=time.time()
    tag=action+'-'+str(time.time_ns())
    (out/(tag+'-stdout-private.json')).write_bytes(response.stdout);(out/(tag+'-stderr-private.txt')).write_bytes(response.stderr)
    if response.returncode:raise RuntimeError('original SSH action failed; fetch this nonce only; retained stderr')
    data=json.loads(response.stdout);data['host_request_bracket']={'real_start':start,'real_end':end}
    if action=='fetch':
        receipt=data['receipt'];validate_receipt(receipt,nonce,allow_missing=True)
        if data['process_state'] not in ['unknown','alive','absent','zombie','pid_reused']:raise ValueError('unknown fetch process label')
        dest=out/tag;dest.mkdir(mode=0o700)
        for name,item in data['files'].items():
            if name in ['.','..'] or Path(name).name!=name or '/' in name or '\\' in name:raise ValueError('invalid fetched evidence path')
            raw=base64.b64decode(item['base64'],validate=True)
            if len(raw)>16*1024*1024 or sha(raw)!=item['sha256'] or name in REVIEWED and sha(raw)!=REVIEWED[name]:raise ValueError('fetched evidence digest mismatch')
            (dest/name).write_bytes(raw)
        result=json.loads((dest/'result.json').read_bytes()) if (dest/'result.json').exists() else None
        if result and (result.get('transaction')!=TX or result.get('host_trigger_nonce')!=nonce):raise ValueError('fetched result nonce differs')
        for name in ['launch-receipt-private.json','execution-started-private.json','config-private.json']:
            path=dest/name
            if not path.exists():continue
            item=json.loads(path.read_bytes())
            if name=='launch-receipt-private.json' and item!=receipt:raise ValueError('two fetched process receipts differ')
            if name=='execution-started-private.json' and (item.get('nonce')!=nonce or receipt and item.get('pid')!=receipt['pid']):raise ValueError('execution marker differs')
            if name=='config-private.json' and (item.get('host_trigger_nonce')!=nonce or item.get('manifest_sha256')!=MANIFEST
                    or item.get('worker_sha256')!=REVIEWED['worker.py'] or item.get('identity',{}).get('boot_id')!=request['expected_boot']):raise ValueError('fetched config identity differs')
        if (dest/'worker.pid').exists() and receipt and int((dest/'worker.pid').read_text())!=receipt['pid']:raise ValueError('worker.pid differs')
        complete=set(REVIEWED)|{'config-private.json','execution-started-private.json','launch-receipt-private.json','worker.pid','result.json'}
        report={'process_state':data['process_state'],'retained_directory':str(dest),'result':result,
                'terminal_verified':bool(complete<=data['files'].keys() and receipt and data['process_state'] in ['absent','zombie'] and result and result.get('terminal') is True and not result.get('mutating_state_unknown',True))}
    else:
        if data.get('launched') is not True:raise ValueError('no confirmed launch; fetch only')
        validate_receipt(data['receipt'],nonce)
        report={'launched':True,'receipt':data['receipt']}
    (out/(tag+'-receipt-private.json')).write_text(json.dumps(data,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['launch','fetch'])
    p.add_argument('--nonce',required=True);p.add_argument('--host-ready-file');p.add_argument('--window-confirmed',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.action,a.nonce,a.host_ready_file,a.window_confirmed),indent=2))
