"""Offline-prepared launch/status/arm/fetch/finish controller. Import is inert."""
from pathlib import Path,PurePosixPath
import argparse
import base64
import importlib.util
import json
import os
import re
import secrets
import time
import common
import gates

HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023/usbin-init-host')
REMOTE_BASE='/root/charging-oem-audit-20261023/usbin-init-host'
RUNTIME=['common.py','protocol.py','gates.py','device.py','observer.py','icon-observation.py','icon-audit.py','samurai-usbin-init.ko']
MUTATING={'launch','arm','finish','close-expired'}

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def local_inputs(require_tests=True):
    pins=json.loads((HERE/'input-pins.json').read_text());values={}
    for name,row in pins.items():
        raw=Path(row['path']).read_bytes()
        if common.sha(raw)!=row['sha256']:raise ValueError('pinned local source differs: '+name)
        values[name]=raw
    r7=load(Path(pins['r7_launcher']['path']),'usbin_reviewed_r7_identity')
    boot,guard,entries=r7.reviewed_identity()
    if common.sha(Path(r7.PINS).read_bytes())!=pins['r7_pins']['sha256']:raise ValueError('R7 identity pin set differs')
    handoff=json.loads(values['r8_handoff'])
    if not(handoff['passed'] and handoff['worker_exited'] and handoff['manifest_sha256']==common.MANIFEST and handoff['loaded_notes_sha256']==common.NOTES):raise ValueError('R8 adoption differs')
    delivery=json.loads(values['helper_delivery']);protocol=json.loads(values['helper_protocol']);build=json.loads(values['helper_build'])
    if not(delivery['passed'] and delivery['kernel']=='7.3.0-rc6-rmx1931-samurai-k363+' and delivery['warnings']==[] and build['passed'] and build['diagnostic_lines']==[] and all(p['returncode']==0 for p in build['phases']) and 'intree:         Y\n' in build['modinfo'] and build['module_sha256']==delivery['module_sha256']):raise ValueError('R2 helper build not verified')
    if protocol['schema']!=1 or protocol['state_path']!='/sys/bus/platform/devices/samurai-usbin-init/state' or protocol['write']!={'address':'0x1358','mask':'0x80','clear_value':0,'restore':'same-instance saved actual masked bit only'}:raise ValueError('helper protocol differs')
    if protocol.get('times',{}).get('window_ms')!=300000:raise ValueError('R2 helper window must be exactly 300000ms')
    files={name:(HERE/name).read_bytes() for name in RUNTIME}
    if common.sha(files['samurai-usbin-init.ko'])!=delivery['module_sha256']:raise ValueError('helper module differs')
    if common.sha(files['icon-observation.py'])!='446cf5dbcbb0ae0a1c765c7b0887c27c4ee978f4d02b590c93be4ff0b3586b21' or common.sha(files['icon-audit.py'])!='7a7c5342fcdef85b5d941d7d9cb351a240d561b9d219817790f63c4825a7a287':raise ValueError('frozen UI read-only code differs')
    if require_tests:
        tested=json.loads((HERE/'test-result.json').read_text())
        if not tested['passed']:raise ValueError('controller tests not passed')
        for name,digest in tested['files'].items():
            if common.sha((HERE/name).read_bytes())!=digest:raise ValueError('tested controller bytes differ: '+name)
    return files,boot,guard,entries

BOOTSTRAP=r'''from pathlib import Path
import base64,hashlib,io,json,os,re,runpy,sys,time
os.umask(0o077);d=json.loads(sys.stdin.buffer.read());action=d['action'];tx=d['transaction']
assert re.fullmatch(r'usbin-init-[a-z0-9][a-z0-9-]{0,35}',tx)
root=Path('/root/charging-oem-audit-20261023/usbin-init-host')/tx
assert str(root)==d['bundle'] and d['capture']==str(root/'capture')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def proc(receipt):
 try:
  p=Path('/proc',str(receipt['pid']));fields=(p/'stat').read_text().rsplit(')',1)[1].split();ticks=int(fields[19]);argv=[v.decode(errors='replace') for v in (p/'cmdline').read_bytes().split(bytes([0])) if v]
  return {'state':'pid_reused' if ticks!=receipt['start_ticks'] else 'zombie' if fields[0]=='Z' else 'alive' if argv==receipt['argv'] else 'unknown','pid':receipt['pid'],'start_ticks':ticks,'argv':argv}
 except FileNotFoundError:return {'state':'absent'}
 except (KeyError,OSError,ValueError,IndexError):return {'state':'unknown'}
if action=='fetch':
 files={};processes={};errors=[]
 if root.exists():
  for p in sorted(root.rglob('*')):
   if p.is_symlink():errors.append('symlink '+str(p));continue
   if p.is_file():
    raw=p.read_bytes()
    if len(raw)>16*1024*1024:errors.append('oversized '+str(p));continue
    files[p.relative_to(root).as_posix()]={'sha256':sha(raw),'base64':base64.b64encode(raw).decode()}
    if p.name.endswith('-process.json'):
     try:processes[p.name]=proc(json.loads(raw))
     except ValueError:errors.append('invalid process receipt '+p.name)
 try:
  a=time.clock_gettime_ns(time.CLOCK_BOOTTIME)//1000000
  state=json.loads(Path('/sys/bus/platform/devices/samurai-usbin-init/state').read_text())
  helper={'state':state,'read_started_ms':a,'read_ended_ms':time.clock_gettime_ns(time.CLOCK_BOOTTIME)//1000000}
 except (OSError,ValueError) as e:helper={'error':str(e)}
 try:identity=Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['expected_boot']==Path(d['guard']).read_text().strip() and sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==d['manifest_sha256']
 except OSError:identity=False
 print(json.dumps({'files':files,'processes':processes,'helper':helper,'identity_unchanged':identity,'fetch_errors':errors,'no_cleanup_or_control_action':True}));sys.exit(0)
assert d['execute'] and d['window_confirmed']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['expected_boot']==Path(d['guard']).read_text().strip()
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==d['manifest_sha256']
if action=='launch':
 assert not root.exists();root.parent.mkdir(parents=True,exist_ok=True,mode=0o700);root.mkdir(mode=0o700)
 assert set(d['file_base64'])==set(d['files'])=={'common.py','protocol.py','gates.py','device.py','observer.py','icon-observation.py','icon-audit.py','samurai-usbin-init.ko'}
 for name,digest in d['files'].items():
  raw=base64.b64decode(d['file_base64'][name],validate=True);assert sha(raw)==digest
  with (root/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 retained={k:v for k,v in d.items() if k!='file_base64'}
 with (root/'request-private.json').open('x') as f:json.dump(retained,f);f.flush();os.fsync(f.fileno())
else:
 retained=json.loads((root/'request-private.json').read_text())
 assert all(retained[k]==d[k] for k in ['transaction','token','expected_boot','files'])
 for name,digest in d['files'].items():assert sha((root/name).read_bytes())==digest
sys.path.insert(0,str(root));sys.stdin=io.StringIO(json.dumps(d));runpy.run_path(str(root/'device.py'),run_name='__main__')
'''

def save_new(path,data):
    with Path(path).open('x') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())

def retain_fetch(data,directory):
    out=directory/('fetch-'+str(time.time_ns()));out.mkdir(mode=0o700)
    for name,row in data.get('files',{}).items():
        rel=PurePosixPath(name)
        if not rel.parts or rel.is_absolute() or '\\' in name or ':' in name or any(p in ('.','..') for p in rel.parts):raise ValueError('unsafe evidence name')
        raw=base64.b64decode(row['base64'],validate=True)
        if common.sha(raw)!=row['sha256']:raise ValueError('fetched evidence bytes differ')
        target=out.joinpath(*rel.parts);target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(raw)
    save_new(out/'fetch-receipt-private.json',data);return out

def run(action,transaction,*,execute=False,window_confirmed=False,user_ready_confirmed=False,terminal_state_confirmed=False,
        ssh=None,private=PRIVATE,require_tests=True):
    if not re.fullmatch(r'usbin-init-[a-z0-9][a-z0-9-]{0,35}',transaction):raise ValueError('fresh transaction name required')
    if action not in ['launch','status','arm','fetch','qualify','finish','close-expired']:raise ValueError('unknown action')
    if not execute or not window_confirmed:raise ValueError('explicit execute/current coordinated window required')
    directory=private/transaction
    if action=='launch':
        files,boot,guard,entries=local_inputs(require_tests)
        directory.parent.mkdir(parents=True,exist_ok=True,mode=0o700);directory.mkdir(mode=0o700)
        c={'transaction':transaction,'token':secrets.token_hex(24),'expected_boot':boot,'guard':guard,'manifest_sha256':common.MANIFEST,
            'bundle':REMOTE_BASE+'/'+transaction,'capture':REMOTE_BASE+'/'+transaction+'/capture','max_seconds':480,
            'files':{name:common.sha(raw) for name,raw in files.items()},'instance':None}
        save_new(directory/'request-private.json',c)
    else:
        c=json.loads((directory/'request-private.json').read_text());entries=local_inputs(require_tests)[3]
        unknown=directory/'unknown-private.json';qualification=directory/'qualification-private.json'
        if unknown.exists() and action not in ['fetch','qualify']:
            q=json.loads(qualification.read_text()) if qualification.exists() else {}
            if action not in ['finish','close-expired'] or q.get('host_unknown_sha256')!=common.sha(unknown.read_bytes()) or q.get('next_action')!=action or not 0<=time.time()-q.get('host_received_realtime',0)<=30:
                raise ValueError('unknown prior mutation; fetch or explicit terminal qualification only')
        if action=='arm' and not user_ready_confirmed:raise ValueError('root must confirm user ready immediately before arm')
        if action in ['qualify','finish','close-expired'] and not terminal_state_confirmed:raise ValueError('root must explicitly review terminal state')
    incoming=dict(c,action=action,execute=True,window_confirmed=True,user_ready_confirmed=user_ready_confirmed,terminal_state_confirmed=terminal_state_confirmed)
    unknown=directory/'unknown-private.json'
    if unknown.exists():incoming['host_unknown_sha256']=common.sha(unknown.read_bytes())
    if action=='launch':incoming['file_base64']={name:base64.b64encode(raw).decode() for name,raw in files.items()}
    if action in MUTATING:
        suffix='-recovery-'+common.sha((directory/'qualification-private.json').read_bytes())[:16] if unknown.exists() else ''
        save_new(directory/(action+suffix+'-intent-private.json'),{k:v for k,v in incoming.items() if k!='file_base64'})
    if ssh is None:ssh=load(Path(entries['transport']['path']),'usbin_strict_ipv6').raw_ssh
    program='import io,sys\nsys.stdin=io.TextIOWrapper(io.BytesIO('+repr(json.dumps(incoming).encode())+'))\n'+BOOTSTRAP
    started=time.monotonic();stamp=str(time.time_ns())
    try:
        response=ssh('python3 -',input=program.encode(),timeout=35,check=False)
        (directory/(action+'-'+stamp+'-stdout-private.json')).write_bytes(response.stdout)
        (directory/(action+'-'+stamp+'-stderr-private.txt')).write_bytes(response.stderr)
        data=json.loads(response.stdout)
        if response.returncode or data.get('operation_unknown'):raise RuntimeError('remote outcome not qualified; retain raw evidence')
        if action=='launch':c['instance']=data['instance'];common.save(directory/'request-private.json',c)
        elif action=='status':
            data['gate']=gates.ready(data,c,not (directory/'arm-known-private.json').exists(),time.monotonic()-started)
        elif action=='arm':save_new(directory/'arm-known-private.json',data)
        elif action=='qualify':
            if data.get('host_unknown_sha256')!=incoming.get('host_unknown_sha256') or any(data.get(k)!=c[k] for k in ['transaction','token']) or data.get('next_action') not in ['finish','close-expired'] or (c['instance'] is not None and data.get('instance')!=c['instance']):raise ValueError('qualification owner/evidence differs')
            c['instance']=data['instance'];common.save(directory/'request-private.json',c)
            common.save(directory/'qualification-private.json',dict(data,host_received_realtime=time.time()))
        elif action=='fetch':data={'retained_directory':str(retain_fetch(data,directory)),'identity_unchanged':data.get('identity_unchanged'),'no_cleanup_performed':True}
        save_new(directory/(action+'-'+stamp+'-result-private.json'),data)
        return data
    except BaseException as e:
        failure={'action':action,'error':str(e),'mutating_outcome_unknown':action in MUTATING,'realtime':time.time()}
        save_new(directory/('error-'+action+'-'+stamp+'-private.json'),failure)
        if action in MUTATING:common.save(directory/'unknown-private.json',failure)
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check-local','launch','status','arm','fetch','qualify','finish','close-expired'])
    p.add_argument('--transaction');p.add_argument('--execute',action='store_true');p.add_argument('--window-confirmed',action='store_true')
    p.add_argument('--user-ready-confirmed',action='store_true');p.add_argument('--terminal-state-confirmed',action='store_true');args=p.parse_args()
    if args.action=='check-local':local_inputs();print(json.dumps({'local_inputs_verified':True,'phone_accessed':False}));return 0
    data=run(args.action,args.transaction,execute=args.execute,window_confirmed=args.window_confirmed,user_ready_confirmed=args.user_ready_confirmed,terminal_state_confirmed=args.terminal_state_confirmed)
    print(json.dumps(data.get('gate',data),indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
