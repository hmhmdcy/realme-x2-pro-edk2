"""Image501 EUD-off host launch/status/fetch for the unchanged read-only icon collector.

Import is inert. No network call occurs except an explicit CLI action.
"""
from pathlib import Path, PurePosixPath
import argparse
import ast
import sys
sys.dont_write_bytecode=True
import base64
import hashlib
import importlib.util
import json
import math
import re
import secrets
import shlex
import time
import uuid

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-image501')
PINS = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/adoption-01-private/icon-identity-pins-private.json')
MIGRATION = HERE / 'template-test-result.json'
MANIFEST = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
FROZEN = {'worker.py': '446cf5dbcbb0ae0a1c765c7b0887c27c4ee978f4d02b590c93be4ff0b3586b21',
          'audit.py': '7a7c5342fcdef85b5d941d7d9cb351a240d561b9d219817790f63c4825a7a287',
          'baseline-test-result.json': '4aeb77e82f845a4f79c6cac44e3779ba3ed86561da2dd0f615e4ff2195b1be0f',
          'capture-entry.py': 'fec4b3fdef5d1433829da77109628a3e7d807b9802117657ad7a09404408c82d'}
REMOTE_BASE = '/root/charging-ui-audit-20261023/icon-capture-image501'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def reviewed_identity(pins=PINS):
    entries=json.loads(pins.read_bytes());evidence={}
    expected={'adoption','adopt_request','adopt_result','endpoint','postboot','receiver','transport','key_transport'}
    if set(entries)!=expected:raise ValueError('Image501 reviewed pin set differs')
    if (Path(entries['transport']['path']).resolve()!=(HERE/'transport.py').resolve()
        or entries['key_transport']['sha256']!='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'):
        raise ValueError('original strict-key transport differs')
    for name,entry in entries.items():
        value=Path(entry['path']).read_bytes()
        if sha(value)!=entry['sha256']:raise ValueError('actual Image501 input changed: '+name)
        if name not in ['transport','key_transport']:evidence[name]=json.loads(value)
    a,r,result,e,post,receiver=[evidence[n] for n in ['adoption','adopt_request','adopt_result','endpoint','postboot','receiver']]
    raw=post['raw'];checks=post['result']['checks']
    if not (a.get('Image501_verified') is True and a.get('original_key_verified') is True and a.get('baseline481_verified') is True
        and a.get('charging_manifest_sha256')==r.get('manifest')==MANIFEST
        and a.get('candidate_boot_sha256')==r.get('candidate_boot_sha256')==raw['boot_partition']['sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
        and a.get('candidate_logdump_sha256')==r.get('candidate_logdump_sha256')==raw['logdump_partition']['sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
        and a.get('postboot_raw_sha256')==r.get('postboot_raw_sha256')==entries['postboot']['sha256']
        and result.get('passed') is True and result.get('guard_created') is True and result.get('old_guards_preserved') is True and result.get('old_pointer_backup_preserved') is True
        and receiver.get('passed') is True and receiver.get('transport_exit')==0
        and post.get('schema')=='samurai-image501-postboot-readonly-v1' and post['result']['passed'] is True
        and checks['R8_install']['R8_disk_and_live_notes'] is True
        and checks['camera481']['camera481_files_packages_notes'] is True
        and checks['EUD_producers']['DT_disabled_no_EUD_cmdline_or_active_producer'] is True
        and checks['instant_gauge']['flag_Y_and_exact_cmdline'] is True
        and checks['instant_gauge']['startup500_native_and_hardware500_preserved'] is True):raise ValueError('actual Image501 fullpair/optin/500 adoption not proved')
    boot,guard=r['boot'],r['guard']
    if str(uuid.UUID(boot))!=boot:raise ValueError('invalid actual boot')
    if guard!=a.get('guard_path') or guard!='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt':raise ValueError('wrong adopted guard')
    if not (raw['identity_before']==raw['identity_after'] and raw['identity_after']['boot_id']==boot
        and r['version']==raw['identity_after']['uname']['version'] and r['version'].startswith('#501 ')
        and e.get('kind')=='usb-ipv6' and e.get('original_key_verified') is True and e.get('postboot_Image501_passed') is True
        and e.get('host_key_alias')=='169.254.42.1' and e.get('interface_index')==29 and e.get('peer')=='fe80::62:bcff:fe28:a101%29'
        and e.get('observed_new_boot')==boot and e.get('guard_path')==guard):raise ValueError('new501 original-key endpoint/boot differs')
    return boot,guard,entries


def runtime_expected(pins=PINS):
    _, _, entries = reviewed_identity(pins)
    r = json.loads(Path(entries['adopt_request']['path']).read_bytes())
    return {k:r[k] for k in ['release','version','rootfs','notes']}


def adopt_local(bundle=HERE, pins=PINS, migration=MIGRATION):
    files = {name: (bundle / name).read_bytes() for name in FROZEN}
    if any(sha(files[name]) != digest for name, digest in FROZEN.items()):
        raise ValueError('frozen generic collector or historical 32-case receipt differs')
    tested = json.loads(files['baseline-test-result.json'])
    if tested.get('passed') is not True or tested.get('tests_run') != 32 or any(
            tested['sha256'][name] != FROZEN[name] for name in ['worker.py', 'audit.py']):
        raise ValueError('generic collector historical tests not proved')
    migrated = json.loads(migration.read_bytes())
    for name,digest in migrated['files'].items():
        if sha((bundle/name).read_bytes())!=digest:raise ValueError('tested template source changed: '+name)
    if not (migrated.get('schema') == 'charging-icon-image501-template-tests-v1' and migrated.get('passed') is True
            and migrated.get('launcher_sha256') == sha((bundle / 'launcher.py').read_bytes())
            and migrated.get('runtime_identity_unbound') is True
            and migrated.get('sha256') == FROZEN and migrated.get('manifest_sha256') == MANIFEST):
        raise ValueError('R7 affected-path test receipt differs')
    boot, guard, entries = reviewed_identity(pins)
    return files, boot, guard


def ready_check(data, request):
    """No guessed liveness: two current observations of this exact worker."""
    reasons = []; observations = data.get('observations', [])
    roundtrip = data.get('host_roundtrip_seconds')
    if not isinstance(roundtrip, (int, float)) or not math.isfinite(roundtrip) or not 0 <= roundtrip <= 8:
        reasons.append('host roundtrip missing or over 8 seconds'); roundtrip = float('inf')
    if data.get('identity_unchanged') is not True: reasons.append('remote boot/guard/manifest identity unproved')
    if len(observations) != 2:
        reasons.append('two observations required')
        return {'may_prompt_user': False, 'reasons': reasons}
    receipt = data.get('launch_receipt', {})
    if type(receipt.get('pid')) is not int or receipt['pid'] <= 0 or type(receipt.get('start_ticks')) is not int or receipt['start_ticks'] <= 0:
        reasons.append('launch PID/start_ticks missing or invalid')
    if any(receipt.get(k) != request.get(k) for k in ['transaction', 'token', 'expected_boot', 'manifest_sha256']):
        reasons.append('launch receipt identity differs from host marker')
    if receipt.get('files') != FROZEN: reasons.append('remote frozen bundle identity differs')
    for index, item in enumerate(observations):
        status, proc = item.get('status', {}), item.get('process', {})
        if proc.get('state') != 'alive': reasons.append(f'observation {index}: exact worker is not alive')
        if any(status.get(k) != receipt.get(k) for k in ['pid', 'start_ticks']):
            reasons.append(f'observation {index}: status PID/start_ticks mismatch')
        if proc.get('pid') != receipt.get('pid') or proc.get('start_ticks') != receipt.get('start_ticks'):
            reasons.append(f'observation {index}: live /proc identity differs')
        if proc.get('argv') != receipt.get('argv') or proc.get('argv') != request.get('argv'):
            reasons.append(f'observation {index}: live cmdline differs')
        if not (status.get('active') is True and status.get('terminal') is False
                and status.get('phase') == 'ready' and status.get('ready_for_user_action') is True):
            reasons.append(f'observation {index}: current status is not ready')
        try:
            age = item['remote_realtime'] - status['realtime']
            remaining = status['remaining_boottime_seconds']
            deadline_remaining = request['max_seconds'] - (item['remote_boottime'] - data['clock_start']['boot'])
            if not all(math.isfinite(v) for v in [age, remaining, deadline_remaining]): raise ValueError()
            if not 0 <= age <= 3: reasons.append(f'observation {index}: status is stale or future-dated')
            if min(remaining, deadline_remaining) - roundtrip < 130:
                reasons.append(f'observation {index}: less than 130 seconds remain')
            if abs(remaining - deadline_remaining) > 3:
                reasons.append(f'observation {index}: deadline accounting differs')
        except (KeyError, TypeError, ValueError): reasons.append(f'observation {index}: timing evidence missing/invalid')
    first, last = observations
    a, b = first.get('status', {}), last.get('status', {})
    if not (type(a.get('tick')) is int and type(b.get('tick')) is int and b['tick'] > a['tick'] >= 3):
        reasons.append('tick did not advance from a valid baseline')
    if not (isinstance(a.get('t'), (int, float)) and isinstance(b.get('t'), (int, float)) and b['t'] > a['t']):
        reasons.append('sample monotonic time did not advance')
    try: spacing = last['remote_boottime'] - first['remote_boottime']
    except (KeyError, TypeError): spacing = float('nan')
    if not 1 <= spacing <= 5:
        reasons.append('observation spacing is not current/bounded')
    return {'may_prompt_user': not reasons, 'reasons': reasons,
            'host_received_realtime': data.get('host_received_realtime'),
            'recheck_if_not_prompted_within_seconds': 3,
            'scope': 'coordinator may now prompt once; this function sends no user message'}


REMOTE = r'''from pathlib import Path
import base64,hashlib,json,os,re,subprocess,sys,time,traceback
data=json.loads(sys.stdin.buffer.read());os.umask(0o077)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
base=Path('/root/charging-ui-audit-20261023/icon-capture-image501')
txn=data['transaction'];assert re.fullmatch(r'charging-icon-[a-z0-9][a-z0-9-]{0,40}',txn)
bundle=base/(txn+'-bundle');out=base/txn
assert str(bundle)==data['remote_bundle'] and str(out)==data['remote_output']
guard=Path(data['guard_path']);assert str(guard).startswith('/var/lib/samurai/') and '..' not in guard.parts and guard.name=='boot-id-private.txt'
def boot_identity():
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 assert boot==data['expected_boot']==guard.read_text().strip()
 return True
def identity():
 boot_identity()
 assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==data['manifest_sha256']
 e=data['identity_expected'];assert os.uname().release==e['release'] and os.uname().version==e['version']
 assert sha(Path('/etc/samurai-rootfs-release').read_bytes())==e['rootfs']
 for name,digest in e['notes'].items():
  assert sha(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes())==digest
  assert Path('/sys/module',name,'initstate').read_text().strip()=='live'
 return True
identity_errors=[]
def checked_identity():
 boot_identity()
 if data['action']!='fetch':return identity()
 try:return identity()
 except Exception:
  identity_errors.append(traceback.format_exc());return False
def save(path,value):
 with path.open('x') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
def read_json(path):
 try:return json.loads(path.read_bytes())
 except (OSError,ValueError):return {}
def process(receipt):
 pid=receipt.get('pid');expected=receipt.get('start_ticks')
 if not isinstance(pid,int):return {'state':'unknown','reason':'launch PID not retained'}
 root=Path('/proc')/str(pid)
 try:
  stat=root.joinpath('stat').read_text();tail=stat[stat.rindex(')')+2:].split();ticks=int(tail[19])
  argv=[x.decode(errors='replace') for x in root.joinpath('cmdline').read_bytes().split(bytes([0])) if x]
 except FileNotFoundError:return {'state':'absent','pid':pid}
 except (OSError,ValueError,IndexError):return {'state':'unknown','pid':pid}
 state='alive' if ticks==expected and argv==receipt.get('argv') and tail[0]!='Z' else 'zombie' if ticks==expected and tail[0]=='Z' else 'pid_reused' if ticks!=expected else 'unknown'
 return {'state':state,'pid':pid,'start_ticks':ticks,'argv':argv}
try:
 identity_before=checked_identity()
 assert data['max_seconds']==300
 if data['action']=='launch':
  assert not bundle.exists() and not out.exists();base.mkdir(mode=0o700,parents=True,exist_ok=True);bundle.mkdir(mode=0o700)
  for name,digest in data['files'].items():
   assert name in ['worker.py','audit.py','baseline-test-result.json','capture-entry.py']
   raw=base64.b64decode(data['file_base64'][name],validate=True);assert sha(raw)==digest
   with (bundle/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  tested=read_json(bundle/'baseline-test-result.json');assert tested['passed'] is True and tested['tests_run']==32
  assert all(tested['sha256'][n]==data['files'][n] for n in ['worker.py','audit.py'])
  save(bundle/'request-private.json',data)
  identity();assert not out.exists()
  argv=data['argv'];assert argv==['python3',str(bundle/'capture-entry.py'),'--execute','--window-confirmed','--transaction',txn,'--output-root',str(base),'--boot-id',data['expected_boot'],'--manifest-sha256',data['manifest_sha256'],'--max-seconds',str(data['max_seconds'])]
  with (bundle/'worker-private.log').open('xb') as log:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   stat=Path('/proc',str(child.pid),'stat').read_text();ticks=int(stat[stat.rindex(')')+2:].split()[19])
  except (OSError,ValueError,IndexError):ticks=None
  receipt={k:data[k] for k in ['transaction','token','expected_boot','manifest_sha256','files','argv']}
  receipt.update(pid=child.pid,start_ticks=ticks);save(bundle/'launch-receipt-private.json',receipt)
  response={'launched':True,'launch_receipt':receipt}
 elif data['action'] in ['status','fetch']:
  retained=read_json(bundle/'request-private.json')
  assert not retained or all(retained.get(k)==data.get(k) for k in ['transaction','token','expected_boot','manifest_sha256','files','argv'])
  receipt=read_json(bundle/'launch-receipt-private.json')
  observations=[]
  for index in range(2 if data['action']=='status' else 1):
   if index:time.sleep(2.2)
   observations.append({'status':read_json(out/'status.json'),'process':process(receipt),
    'remote_realtime':time.time(),'remote_boottime':time.clock_gettime(time.CLOCK_BOOTTIME)})
  response={'launch_receipt':receipt,'clock_start':read_json(out/'clock-start.json'),'observations':observations}
  if data['action']=='fetch':
   files={}
   for label,directory in [('bundle',bundle),('capture',out)]:
    if directory.exists():
     for path in sorted(directory.rglob('*')):
      assert not path.is_symlink()
      if path.is_file():
       raw=path.read_bytes();assert len(raw)<=16*1024*1024
       files[label+'/'+path.relative_to(directory).as_posix()]={'sha256':sha(raw),'base64':base64.b64encode(raw).decode()}
   response['files']=files
   capture=read_json(out/'capture-private.json');status=observations[0]['status'];monitor=capture.get('monitor',{})
   response['cleanup_state']={'exact_worker_state':observations[0]['process']['state'],
    'worker_terminal':status.get('terminal') is True and status.get('active') is False,
    'monitor_started':monitor.get('started'),'monitor_errors':monitor.get('errors'),
    'dbus_returncode':monitor.get('dbus_returncode'),'no_stop_or_cleanup_action_performed':True}
 else:raise ValueError('invalid action')
 identity_after=checked_identity()
 response['identity_unchanged']=identity_before and identity_after
 response['identity_errors']=identity_errors;print(json.dumps(response),flush=True)
except BaseException:
 print(json.dumps({'remote_error':traceback.format_exc()}),flush=True);sys.exit(1)
'''


def transport(pins=PINS):
    _, _, entries = reviewed_identity(pins)
    spec = importlib.util.spec_from_file_location('icon_r7_ipv6', entries['transport']['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.raw_ssh


def save_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2); stream.flush()
        import os
        os.fsync(stream.fileno())


def retain_fetch(data, directory):
    destination = directory / ('fetch-' + str(time.time_ns())); destination.mkdir(mode=0o700)
    for name, file in data.get('files', {}).items():
        rel = PurePosixPath(name)
        if (rel.is_absolute() or '\\' in name or ':' in name or any(p in ['.', '..'] for p in rel.parts)
                or not rel.parts or rel.parts[0] not in ['bundle', 'capture']):
            raise ValueError('unsafe fetched evidence name')
        raw = base64.b64decode(file['base64'], validate=True)
        if sha(raw) != file['sha256']: raise ValueError('fetched evidence hash mismatch')
        target = destination.joinpath(*rel.parts); target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(raw)
    save_new(destination / 'fetch-receipt-private.json', data)
    return destination


def cleanup_check(state):
    return bool(state.get('exact_worker_state') in ['absent', 'zombie', 'pid_reused']
                and state.get('worker_terminal') is True and state.get('monitor_started') is True
                and state.get('monitor_errors') == [] and type(state.get('dbus_returncode')) is int)


def run(action, transaction, confirmed=False, *, ssh=None, private=PRIVATE,
        bundle=HERE, pins=PINS, migration=MIGRATION, max_seconds=300):
    if action not in ['launch', 'status', 'fetch']: raise ValueError('invalid action')
    if not re.fullmatch(r'charging-icon-[a-z0-9][a-z0-9-]{0,40}', transaction): raise ValueError('invalid transaction')
    directory = private / transaction
    if action == 'launch':
        if not confirmed: raise ValueError('explicit camera/Bluetooth handback required before launch')
        if max_seconds != 300: raise ValueError('this reviewed capture has a fixed 300-second deadline')
        files, boot, guard = adopt_local(bundle, pins, migration)
        directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True); directory.mkdir(mode=0o700)
        remote_bundle = REMOTE_BASE + '/' + transaction + '-bundle'
        request = dict(transaction=transaction, token=secrets.token_hex(24), expected_boot=boot,
                       manifest_sha256=MANIFEST, guard_path=guard, files=FROZEN,
                       remote_bundle=remote_bundle, remote_output=REMOTE_BASE + '/' + transaction,
                       max_seconds=max_seconds, dispatch_count=1, identity_pins_sha256=sha(pins.read_bytes()),
                       candidate_revision="image501-eud-off-300-v1", identity_expected=runtime_expected(pins))
        request['argv'] = ['python3', remote_bundle + '/capture-entry.py', '--execute', '--window-confirmed',
                           '--transaction', transaction, '--output-root', REMOTE_BASE,
                           '--boot-id', boot, '--manifest-sha256', MANIFEST, '--max-seconds', str(max_seconds)]
        # Must survive an unknown SSH/Popen outcome. This transaction then becomes status/fetch only.
        save_new(directory / 'launch-request-private.json', request)
        payload = {**request, 'file_base64': {n: base64.b64encode(raw).decode() for n, raw in files.items()}}
    else:
        reviewed_identity(pins)
        request = json.loads((directory / 'launch-request-private.json').read_bytes())
        if request['transaction'] != transaction or request['files'] != FROZEN or request['manifest_sha256'] != MANIFEST or request.get('identity_pins_sha256') != sha(pins.read_bytes()) or request.get('identity_expected') != runtime_expected(pins):
            raise ValueError('host launch marker differs from this reviewed collector')
        payload = dict(request)
    payload['action'] = action
    tag = action + '-' + str(time.time_ns())
    dispatched = time.monotonic()
    try:
        call = ssh if ssh is not None else transport(pins)
        response = call('python3 -c ' + shlex.quote(REMOTE), input=json.dumps(payload).encode(), timeout=45, check=False)
    except BaseException as failure:
        save_new(directory / (tag + '-transport-error-private.json'), {'type': type(failure).__name__, 'message': str(failure)})
        raise
    (directory / (tag + '-stdout-private.json')).write_bytes(response.stdout)
    (directory / (tag + '-stderr-private.txt')).write_bytes(response.stderr)
    if response.returncode: raise RuntimeError('remote action failed; retained original stdout/stderr, no retry')
    data = json.loads(response.stdout)
    data['host_roundtrip_seconds'] = time.monotonic() - dispatched
    data['host_received_realtime'] = time.time()
    if action == 'launch':
        receipt = data.get('launch_receipt', {})
        verified = (all(receipt.get(k) == request.get(k) for k in
                        ['transaction', 'token', 'expected_boot', 'manifest_sha256', 'files', 'argv'])
                    and type(receipt.get('pid')) is int and receipt['pid'] > 0
                    and type(receipt.get('start_ticks')) is int and receipt['start_ticks'] > 0)
        result = {'launched': data.get('launched') is True, 'pid': receipt.get('pid'),
                  'start_ticks': receipt.get('start_ticks'), 'launch_receipt_verified': verified,
                  'may_prompt_user': False}
    elif action == 'status': result = ready_check(data, request)
    else:
        retained = retain_fetch(data, directory)
        result = {'fetched': True, 'retained_directory': str(retained), 'cleanup_state': data.get('cleanup_state'),
                  'cleanup_confirmed': cleanup_check(data.get('cleanup_state', {})),
                  'identity_unchanged': data.get('identity_unchanged'), 'may_prompt_user': False}
    save_new(directory / (tag + '-result.json'), result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='check-local', choices=['check-local','launch','status','fetch'])
    parser.add_argument('--transaction'); parser.add_argument('--window-confirmed', action='store_true')
    parser.add_argument('--max-seconds', type=int, default=300)
    args = parser.parse_args(argv)
    if args.action == 'check-local':
        for name,digest in FROZEN.items():
            if sha((HERE/name).read_bytes())!=digest:raise ValueError('frozen source differs: '+name)
        for name in ['launcher.py','capture-entry.py','worker.py','audit.py']:ast.parse((HERE/name).read_text())
        tested=json.loads(MIGRATION.read_bytes())
        if not tested['passed']:raise ValueError('template tests not passed')
        for name,digest in tested['files'].items():
            if sha((HERE/name).read_bytes())!=digest:raise ValueError('tested template source changed: '+name)
        if PINS.exists():adopt_local()
        print(json.dumps({'local_sources_verified':True,'device_accessed':False,'runtime_identity_available':PINS.exists(),'deadline_seconds':300})); return
    if not args.transaction: raise ValueError('fresh transaction required')
    print(json.dumps(run(args.action, args.transaction, args.window_confirmed, max_seconds=args.max_seconds), indent=2))


if __name__ == '__main__': main()
