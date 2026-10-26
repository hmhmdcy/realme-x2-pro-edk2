"""Only R8 identity/guard/port changes; no device/SSH/USB or old suites."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,copy,datetime,hashlib,importlib.util,json,tempfile
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('new_usb500_host',HERE/'host-launcher.py');w=load('new_usb500_worker',HERE/'device-candidate/worker.py')
before=h.load_baseline(PRIVATE);actual=before['raw'];cases=[]
def ok(label,value=True):assert value,label;cases.append(label)
def refuses(fn):
 try:fn()
 except (ValueError,RuntimeError,KeyError):return
 raise AssertionError('missing refusal')
ok('actual exact R3/R8 SDP100 baseline and new module identities accepted')
with tempfile.TemporaryDirectory(prefix='usb500-r8-identity-') as td:
 p=Path(td);bp=p/h.BASELINE_REL;ep=p/h.ENDPOINT_REL;bp.parent.mkdir(parents=True)
 adopted=json.loads((PRIVATE/'boot-adoption-private.json').read_bytes());endpoint=json.loads((PRIVATE/h.ENDPOINT_REL).read_bytes())
 def store(b,a=adopted,e=endpoint):
  raw=json.dumps(b).encode();bp.write_bytes(raw);(p/'boot-adoption-private.json').write_text(json.dumps(a));ep.write_text(json.dumps(e));return h.sha(raw)
 original=json.loads((PRIVATE/h.BASELINE_REL).read_bytes())
 bad=copy.deepcopy(original);bad['raw']['manifest']['sha256']='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
 with patch.object(h,'BASELINE_SHA',store(bad)):refuses(lambda:h.load_baseline(p))
 bad=copy.deepcopy(original);bad['raw']['charging_modules']['samurai-mp2650']['loaded_note_sha256']='0'*64
 with patch.object(h,'BASELINE_SHA',store(bad)):refuses(lambda:h.load_baseline(p))
 ok('actual R8 loader rejects R7 manifest or mismatched new charger live note')
 for mutate in ['old_guard','old_flag','old_boot']:
  a=copy.deepcopy(adopted);e=copy.deepcopy(endpoint)
  if mutate=='old_guard':a['guard_path']='/var/lib/samurai/k449-adopted/boot-id-private.txt'
  if mutate=='old_flag':a.pop('baseline481_verified');a['baseline440_verified']=True
  if mutate=='old_boot':e['observed_new_boot']='old-boot'
  with patch.object(h,'BASELINE_SHA',store(original,a,e)):refuses(lambda:h.load_baseline(p))
 ok('actual adoption rejects old guard/440 flag or mismatched boot')

# Real begin runs to its first window/lock boundary, with only file edges fake.
class ReachedWindow(Exception):pass
class FakeDirectory:
 def __str__(self):return w.PREFIX+'a'*48
 def is_symlink(self):return False
 def stat(self):return SimpleNamespace(st_uid=0,st_mode=0o40700)
class HardwarePath:
 def __init__(self,*parts):self.value='/'.join(map(str,parts))
 def read_bytes(self):return b'realme,samurai\0' if self.value.endswith('compatible') else b'fixture-serial'
 def read_text(self):assert self.value.endswith('/name');return 'mp2650\n'
 def resolve(self):return self
 def as_posix(self):return '/soc@0/geniqup@8c0000/i2c@884000/charger@5c'
class Begin:
 directory=FakeDirectory()
 def read_owned(self,path):return ((HERE/'device-candidate/worker.py').read_bytes(),0o600)
 def check_window(self,c):raise ReachedWindow
ready=dict(armed=True,target_port=255,remaining_seconds_at_trigger=120,decoder_sha256=h.DECODER,collector_sha256=h.COLLECTOR,
 host_worker_pid=1,capture_id='usb500-r8-eud-off-'+'a'*48,armed_utc='2026-10-24T00:00:00+00:00')
c=dict(transaction=w.TX,guard=w.r6.GUARD,manifest_sha256=w.r6.NEW,identity={'compatible_sha256':h.sha(b'realme,samurai\0'),'serial_sha256':h.sha(b'fixture-serial')},
 window_token='fixture',host_trigger_nonce='a'*48,host_ready=ready,host_trigger_utc=ready['armed_utc'],worker_sha256=h.sha((HERE/'device-candidate/worker.py').read_bytes()))
with patch.object(w,'Path',HardwarePath),patch.object(w.os,'uname',return_value=SimpleNamespace(release=w.r6.RELEASE)):
 try:w.Diagnostic.begin(Begin(),c)
 except ReachedWindow:pass
 else:raise AssertionError('did not reach unchanged window boundary')
 for name,value in [('guard','/var/lib/samurai/k449-adopted/boot-id-private.txt'),('manifest_sha256','5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68')]:
  bad=copy.deepcopy(c);bad[name]=value;refuses(lambda:w.Diagnostic.begin(Begin(),bad))
 for port in [0,256]:
  bad=copy.deepcopy(c);bad['host_ready']['target_port']=port;refuses(lambda:w.Diagnostic.begin(Begin(),bad))
 bad=copy.deepcopy(c);bad['host_ready']['capture_id']='usb500-r7-'+'a'*48;refuses(lambda:w.Diagnostic.begin(Begin(),bad))
ok('actual worker begin accepts direct-root255 and rejects old guard/manifest/capture or out-of-byte port')

# Synthetic register edge values accompany actual R3 telemetry; not a new readback.
sample={k:int(v,0) for k,v in (item.split('=',1) for item in actual['telemetry_after'].split())}
row={'sample':sample,'registers':{'00':2,'0f':2,'02':5,'04':104,'08':0x10},'source':actual['source'],'udc':'configured',
 'limits':{'native_ua':100000,'source_budget_ua':100000,'input_ua':100000,'charge_ua':250000,'cv_uv':4362500}}
ok('actual R3 telemetry through unchanged SDP100 receiver',w.accepted(copy.deepcopy(row),100)=='managed')
full=copy.deepcopy(row);full['sample'].update(logical_full=1,hold_requested=1,full_holding=1,full_cause=1,desired_enable=0,session_seconds=0);full['registers']['08']=0
ok('exact healthy Full remains eligible with unchanged receiver',w.accepted(full,100)=='full_holding')
def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,ast.FunctionDef)}
old=REF/'charging-oem-audit-20261023/usb500-r7-candidate'
a=functions(old/'device-candidate/worker.py');b=functions(HERE/'device-candidate/worker.py')
same=['configure','accepted','stable','transaction','gadget_state','write','net_command','network','check_window','event','finish','snapshot']
ok('real one500/finally100, no CHG/AUTO/INHIBIT, timeout/unknown/no-next-mutation bodies unchanged',all(a[n]==b[n] for n in same))
compile(h.REMOTE_LAUNCH,'remote-launch','exec');compile(h.REMOTE_FETCH,'remote-fetch','exec')
gate=dict(owned_handle_checked=True,host_trigger_utc='2026-10-24T00:00:01+00:00',host_ready={**ready,'ready_at_utc':'2026-10-24T00:00:00+00:00'})
now=datetime.datetime.fromisoformat(gate['host_trigger_utc']).timestamp()
h.validate_gate(gate,'a'*48,now)
bad=copy.deepcopy(gate);bad['host_ready']['target_port']=256;refuses(lambda:h.validate_gate(bad,'a'*48,now))
ok('host programs compile and fresh byte-port gate rejects256')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'schema':'usb500-r8-eud-off-migration-v1','passed':True,'cases':len(cases),'sequences':cases,
 'tested_files':{n:sha(HERE/'device-candidate'/n) for n in ['worker.py','r8-base.py','health.py']},
 'test_source_sha256':sha(Path(__file__)),'actual_r3_sha256':h.BASELINE_SHA,
 'unchanged_control_functions':same,'fake_register_edges':True,'frozen_suites_rerun':False,'device_access':False,'usb_access':False,'sdk_access':False}
(HERE/'device-candidate/test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_cases':len(cases),'device_access':False,'usb_access':False}))
