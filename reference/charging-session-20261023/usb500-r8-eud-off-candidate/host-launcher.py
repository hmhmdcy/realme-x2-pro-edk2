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
TX = 'usb500-r8-eud-off-diagnostic-v1'
PREFIX = '/root/charging-management-20261023/' + TX + '-'
MANIFEST = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
DECODER = '90dcc5eba45ba3f7b225b0670c70562ed7fb62a3f1df965b43d09f19dbbbc01b'
COLLECTOR = '2ba976fedcc13583171dd2e51d3df64187497889b6ec53f5155a277baab58309'
GUARD = '/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt'
TRANSPORT_SHA = 'f493a73a3eaf17cac4a56ac68b2cdffc90f52d6783eaae4beed5bb6307fd3336'
BASELINE_REL = 'eud-boot-activation/eud-boot-r2-live-001/postboot-r3-01-private/stdout-private.json'
BASELINE_SHA = 'a648abd2558d49f66f1d6c5e1088690826186aa7dff2609f708b49a1ff7b30fd'
ENDPOINT_REL = 'eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json'
CANDIDATE_BOOT = '4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
MODULES = {'samurai-mp2650': {'sha256': '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f', 'note_sha256': 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}, 'samurai-usb-input': {'sha256': '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70', 'note_sha256': 'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0'}, 'samurai-gauge-protection': {'sha256': '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7', 'note_sha256': '930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76'}}
REVIEWED = {'worker.py': 'dacd8cb690a6c10f78a48a88797c4a3f9719f2b8173ee58eaad9cfe2ee36973f', 'r8-base.py': '3b4f1f41942379b18703bfbfc114fb8ba9e8d33d98265770aaaec975e58ee203', 'health.py': 'a41942f21773c97b22d0b3760b1e256650f8e5506ee6cd0883db7145a39f4b4f', 'test-result.json': '26b6693e5a08266e678c53448294d1b7673a1f45e9838216ea3c4dadf536b5ba'}
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
            and type(ready['target_port']) is int and 1 <= ready['target_port'] <= 255
            and ready['remaining_seconds_at_trigger'] >= 110
            and ready['capture_id'] == 'usb500-r8-eud-off-' + nonce
            and ready['decoder_sha256'] == DECODER and ready['collector_sha256'] == COLLECTOR):
        raise ValueError('actual owned reader/remaining time/identity is unproved')
    stamp=dt.datetime.fromisoformat(ready['ready_at_utc'])
    if stamp.utcoffset() is None: raise ValueError('explicit sweep UTC offset required')
    ready_at = stamp.timestamp()
    if not 0 <= when - ready_at <= 3: raise ValueError('last complete armed sweep is stale')


def load_baseline(private):
    content=(private/BASELINE_REL).read_bytes()
    if sha(content)!=BASELINE_SHA:raise ValueError('exact adopted R3 baseline bytes required')
    before=json.loads(content); raw=before['raw']; result=before['result']
    adoption=json.loads((private/'boot-adoption-private.json').read_bytes())
    endpoint=json.loads((private/ENDPOINT_REL).read_bytes())
    manifest=json.loads(raw['manifest_text'])
    if not (before['schema']=='samurai-eud-postboot-readonly-v1' and result['passed'] is True
            and result['read_only'] is True and result['hardware_writes']==0
            and raw['manifest']['sha256']==MANIFEST
            and result['checks']['R8_install']['R8_disk_and_live_notes'] is True
            and result['checks']['camera481']['camera481_files_packages_notes'] is True
            and result['checks']['EUD_producers']['DT_disabled_no_EUD_cmdline_or_active_producer'] is True
            and result['checks']['EUD_ring_receipt']['ready'] is True
            and result['checks']['charging']['ready'] is True
            and result['checks']['charging']['source_type']=='SDP'
            and all(result['checks']['charging'][k]==100000 for k in ['budget_ua','native_ua','input_ua'])
            and raw['config_max_power_ma']=='100'
            and raw['source']['usb_type']=='Unknown [SDP] DCP CDP C'
            and raw['source']['online']=='1'
            and raw['source']['current_max']==raw['source']['input_current_limit']=='100000'):
        raise ValueError('complete adopted R8/EUD-off SDP100 baseline required; not a fresh device gate')
    if set(raw['charging_modules'])!=set(MODULES):raise ValueError('exact R8 module set')
    for name,pin in MODULES.items():
        module=raw['charging_modules'][name]
        if not (module['sha256']==pin['sha256']==manifest['modules'][name]['sha256']
                and module['loaded_note_sha256']==module['disk_note_sha256']==pin['note_sha256']
                and module['loaded_note_matches_disk'] is True and raw['charging_module_live'][name]=='live'):
            raise ValueError('actual R8 disk/live module identity differs: '+name)
    boot=raw['identity_after']['boot_id']
    if not (raw['identity_before']==raw['identity_after']
            and adoption['original_key_verified'] is True and adoption['baseline481_verified'] is True
            and adoption['charging_manifest_sha256']==MANIFEST and adoption['guard_path']==GUARD
            and adoption['candidate_boot_sha256']==raw['boot_partition']['sha256']==CANDIDATE_BOOT
            and adoption['postboot_raw_sha256']==BASELINE_SHA
            and endpoint['kind']=='usb-ipv6' and endpoint['original_key_verified'] is True
            and endpoint['postboot_R3_passed'] is True and endpoint['guard_path']==GUARD
            and endpoint['peer']=='fe80::62:bcff:fe28:a101%29' and endpoint['interface_index']==29
            and endpoint['host_key_alias']=='169.254.42.1' and endpoint['observed_new_boot']==boot):
        raise ValueError('new R8/EUD-off adoption/481/IPv6/boot guard disagree')
    before['state']={'boot_id':boot}
    return before


def transport():
    # Fixed observed IPv6 + original HostKeyAlias. Never the optional IPv4 path.
    load_baseline(PRIVATE)
    source=HERE.parents[1]/'charging-management-20261023/eud-postboot-transport.py'
    if sha(source.read_bytes())!=TRANSPORT_SHA:raise ValueError('reviewed original-key IPv6 helper changed')
    spec=importlib.util.spec_from_file_location('usb500_r8_eud_off_ipv6',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def same_boot(command,**kwargs):
        module.raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(GUARD),timeout=15).check_returncode()
        return module.raw_ssh(command,**kwargs)
    return same_boot


def validate_receipt(receipt, nonce, allow_missing=False):
    if not receipt and allow_missing:return
    expected=['python3','-B',PREFIX+nonce+'/worker.py','--worker',PREFIX+nonce]
    if not (type(receipt.get('pid')) is int and receipt['pid']>0 and type(receipt.get('start_ticks')) is int and receipt['start_ticks']>0
            and receipt.get('argv')==expected and receipt.get('worker_sha256')==REVIEWED['worker.py']):
        raise ValueError('process receipt identity differs')


REMOTE_LAUNCH = r'''from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
data=json.loads(sys.stdin.buffer.read());os.umask(0o077);assert os.geteuid()==0 and not sys.flags.optimize
root=Path(data['remote']);assert str(root)=='/root/charging-management-20261023/usb500-r8-eud-off-diagnostic-v1-'+data['nonce']
guard=Path('/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt');assert data['guard']==str(guard)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==data['expected_boot']==guard.read_text().strip()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['manifest_sha256']
lease=Path('/run/samurai-usb500-r8-eud-off-window.json');assert not lease.exists()
old=[b'/root/charging-management-20261023/charging-pm-r5.py',b'/root/charging-management-20261023/usb-reenumerate/worker.py',b'/root/charging-management-20261023/usb-power500/worker.py',b'/root/charging-management-20261023/usb-hotplug-r4/worker.py',b'/root/charging-management-20261023/charging-update-r6-runner.py',b'/root/charging-management-20261023/r6-smoke-runner.py']
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:args=p.read_bytes().split(bytes([0]))
 except FileNotFoundError:continue
 assert not any(a in old or a.startswith((b'/root/charging-management-20261023/usb500-r6-diagnostic-v1-',b'/root/charging-management-20261023/usb500-r7-diagnostic-v1-',b'/root/charging-management-20261023/usb500-r8-eud-off-diagnostic-v1-')) and a.endswith(b'/worker.py') for a in args),'prior worker still live'
root.mkdir(mode=0o700)
for name,item in data['files'].items():
 assert name in ['worker.py','r8-base.py','health.py','test-result.json']
 raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256']
 with (root/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert {n:sha((root/n).read_bytes()) for n in data['reviewed']}==data['reviewed']
tested=json.loads((root/'test-result.json').read_bytes());assert tested['passed'] is True and tested['schema']=='usb500-r8-eud-off-migration-v1' and tested['cases']>=8
assert all(tested['tested_files'][n]==data['files'][n]['sha256'] for n in ['worker.py','r8-base.py','health.py'])
serial=Path('/sys/devices/soc0/serial_number').read_bytes();assert serial.strip()
compat=Path('/sys/firmware/devicetree/base/compatible').read_bytes();assert b'realme,samurai' in compat.split(bytes([0]))
ready=dict(data['gate']['host_ready']);ready['armed_utc']=ready['ready_at_utc']
config={'transaction':'usb500-r8-eud-off-diagnostic-v1','guard':str(guard),'manifest_sha256':data['manifest_sha256'],
 'identity':{'boot_id':boot,'serial_sha256':sha(serial),'compatible_sha256':sha(compat)},
 'window_token':data['token'],'host_trigger_nonce':data['nonce'],'host_ready':ready,
 'host_trigger_utc':data['gate']['host_trigger_utc'],'worker_sha256':data['files']['worker.py']['sha256']}
def save(path,obj):
 with path.open('x') as f:json.dump(obj,f);f.flush();os.fsync(f.fileno())
save(root/'config-private.json',config)
save(lease,{'transaction':'usb500-r8-eud-off-diagnostic-v1','owner':'charging','camera_released':True,'bluetooth_released':True,
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
    out = private / ('usb500-r8-eud-off-' + nonce)
    if action == 'launch':
        if not confirmed: raise ValueError('explicit camera/Bluetooth handback required')
        gate = json.loads(Path(gate_file).read_bytes()); validate_gate(gate, nonce, time.time())
        candidate = HERE / 'device-candidate'; tested = json.loads((candidate/'test-result.json').read_bytes())
        if tested['passed'] is not True or tested.get('schema')!='usb500-r8-eud-off-migration-v1' or tested['cases']<8: raise ValueError('unqualified device candidate')
        files = {}
        for name in ['worker.py','r8-base.py','health.py','test-result.json']:
            raw=(candidate/name).read_bytes(); digest=sha(raw)
            if digest!=REVIEWED[name]:raise ValueError('different reviewed R7 migration candidate/receipt')
            if name!='test-result.json' and digest!=tested['tested_files'][name]: raise ValueError('untested candidate bytes')
            files[name]={'sha256':digest,'base64':base64.b64encode(raw).decode()}
        before=load_baseline(private)
        import secrets
        request={'nonce':nonce,'remote':PREFIX+nonce,'expected_boot':before['state']['boot_id'],
                 'manifest_sha256':MANIFEST,'guard':GUARD,'token':secrets.token_hex(24),'gate':gate,'files':files,'dispatch_count':1,'reviewed':REVIEWED}
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
                    or item.get('guard')!=GUARD or item.get('transaction')!=TX or item.get('worker_sha256')!=REVIEWED['worker.py'] or item.get('identity',{}).get('boot_id')!=request['expected_boot']):raise ValueError('fetched config identity differs')
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


def check_local():
    load_baseline(PRIVATE)
    source=HERE.parents[1]/'charging-management-20261023/eud-postboot-transport.py'
    if sha(source.read_bytes())!=TRANSPORT_SHA:raise ValueError('new exact transport required')
    compile(source.read_bytes(),str(source),'exec')
    compile(REMOTE_LAUNCH,'remote-launch','exec');compile(REMOTE_FETCH,'remote-fetch','exec')
    for name,digest in REVIEWED.items():
        if sha((HERE/'device-candidate'/name).read_bytes())!=digest:raise ValueError('unqualified candidate bytes')
    return {'checked_local_only':True,'profile':'R8/EUD-off','device_accessed':False,'usb_accessed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',nargs='?',default='check-local',choices=['check-local','launch','fetch'])
    p.add_argument('--nonce');p.add_argument('--host-ready-file');p.add_argument('--window-confirmed',action='store_true')
    a=p.parse_args()
    print(json.dumps(check_local() if a.action=='check-local' else run(a.action,a.nonce,a.host_ready_file,a.window_confirmed),indent=2))
