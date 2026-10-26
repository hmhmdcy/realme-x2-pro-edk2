"""Directed R7 identity/IPv6/receiver tests with fake transport only."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,datetime as dt,hashlib,importlib.util,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r7_launcher',HERE/'host-launcher.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
P=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
baseline=h.load_baseline(P)
adoption=json.loads((P/'boot-adoption-private.json').read_bytes())
endpoint=json.loads((P/'r7-postboot/usb-ipv6-transport-private.json').read_bytes())
cases=[]
def ok(name,value=True):assert value,name;cases.append(name)
def refuse(fn):
 try:fn()
 except (ValueError,RuntimeError,FileExistsError):return
 raise AssertionError('missing refusal')
NONCE='a'*48;NOW=dt.datetime(2026,10,23,0,0,10,tzinfo=dt.timezone.utc).timestamp()
gate=dict(owned_handle_checked=True,host_trigger_utc='2026-10-23T00:00:10+00:00',host_ready=dict(
 armed=True,target_port=7,remaining_seconds_at_trigger=120,decoder_sha256=h.DECODER,collector_sha256=h.COLLECTOR,
 host_worker_pid=123,capture_id='usb500-r7-'+NONCE,ready_at_utc='2026-10-23T00:00:09+00:00'))
h.validate_gate(gate,NONCE,NOW)
bad=copy.deepcopy(gate);bad['host_ready']['capture_id']='usb500-r6-'+NONCE
refuse(lambda:h.validate_gate(bad,NONCE,NOW))
ok('R7 capture gate accepts only new R7 capture identity; source pins unchanged')
compile(h.REMOTE_LAUNCH,'remote-launch','exec');compile(h.REMOTE_FETCH,'remote-fetch','exec')
tree=ast.parse(h.REMOTE_LAUNCH)
nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ready','config') or isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='ready' for t in n.targets)]
env={'data':dict(gate=gate,manifest_sha256=h.MANIFEST,token='token',nonce=NONCE,files={'worker.py':{'sha256':h.REVIEWED['worker.py']}}),
 'guard':h.GUARD,'boot':baseline['state']['boot_id'],'serial':b'fixture','compat':b'fixture','sha':h.sha}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'real-remote-map','exec'),env)
assert env['config']['guard']==h.GUARD and env['config']['transaction']==h.TX and env['config']['manifest_sha256']==h.MANIFEST
assert env['config']['host_ready']['armed_utc']==gate['host_ready']['ready_at_utc']
ok('actual R7 remote config mapping and source programs compile')

with tempfile.TemporaryDirectory(prefix='usb500-r7-host-fixtures-') as td:
 private=Path(td);(private/'r7-handoff').mkdir();(private/'r7-postboot').mkdir()
 # Only the tested fields are copied; don't need a full dmesg fixture.
 stored=copy.deepcopy(baseline);stored.pop('dmesg',None)
 bp=private/'r7-handoff/snapshot-private.json';ap=private/'boot-adoption-private.json';ep=private/'r7-postboot/usb-ipv6-transport-private.json'
 def store(b=stored,a=adoption,e=endpoint):
  bp.write_text(json.dumps(b));ap.write_text(json.dumps(a));ep.write_text(json.dumps(e))
 store();assert h.load_baseline(private)['state']['boot_id']==baseline['state']['boot_id']
 for field,value in [('manifest_sha256','944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'),('passed',False)]:
  bad=copy.deepcopy(stored);bad['result'][field]=value;store(bad);refuse(lambda:h.load_baseline(private))
 bad=copy.deepcopy(adoption);bad['guard_path']='/var/lib/samurai/k449-adopted/boot-id-private.txt';store(a=bad);refuse(lambda:h.load_baseline(private))
 bad=copy.deepcopy(endpoint);bad['peer']='fe80::1%29';store(e=bad);refuse(lambda:h.load_baseline(private))
 bad=copy.deepcopy(endpoint);bad['observed_new_boot']='old-boot';store(e=bad);refuse(lambda:h.load_baseline(private))
 store();ok('R7 baseline binds original-key manifest newguard observed peer and same newboot')

 # Test actual transport closure without importing or calling the SSH module.
 calls=[]
 def fake_raw(command,**kwargs):calls.append((command,kwargs));return subprocess.CompletedProcess('fake-original-key-IPv6',0,b'{}',b'')
 fake=SimpleNamespace(raw_ssh=fake_raw)
 loader=SimpleNamespace(exec_module=lambda module:None)
 with patch.object(h,'PRIVATE',private),patch.object(h.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)),patch.object(h.importlib.util,'module_from_spec',return_value=fake):
  route=h.transport();route('fake-read-only',timeout=3)
  assert len(calls)==2 and calls[0][0].endswith(h.GUARD) and calls[1][0]=='fake-read-only'
  with patch.object(h,'TRANSPORT_SHA','0'*64):refuse(h.transport)
 ok('actual IPv6-only transport checks original helper hash and current boot without fallback')

 gf=private/'gate.json';gf.write_text(json.dumps(gate));dispatched=[]
 def unknown(command,**kw):dispatched.append(json.loads(kw['input']));raise subprocess.TimeoutExpired('fake-only',30)
 with patch.object(h.time,'time',return_value=NOW):
  try:h.run('launch',NONCE,gf,True,ssh=unknown,private=private)
  except subprocess.TimeoutExpired:pass
  else:raise AssertionError('unknown outcome swallowed')
  refuse(lambda:h.run('launch',NONCE,gf,True,ssh=unknown,private=private))
 assert len(dispatched)==1 and dispatched[0]['guard']==h.GUARD and dispatched[0]['expected_boot']==stored['state']['boot_id']
 ok('actual unknown R7 dispatch is durable fetch-only, never relaunched')

 def envelope():
  receipt=dict(pid=42,start_ticks=12345,argv=['python3','-B',h.PREFIX+NONCE+'/worker.py','--worker',h.PREFIX+NONCE],worker_sha256=h.REVIEWED['worker.py'])
  files={n:(HERE/'device-candidate'/n).read_bytes() for n in h.REVIEWED}
  config=dict(transaction=h.TX,guard=h.GUARD,host_trigger_nonce=NONCE,manifest_sha256=h.MANIFEST,
   worker_sha256=h.REVIEWED['worker.py'],identity={'boot_id':stored['state']['boot_id']})
  result=dict(transaction=h.TX,host_trigger_nonce=NONCE,terminal=True,mutating_state_unknown=False,
   passed=False,restore100_verified=False,final_observation={'source':{'input_current_limit':'100000','current_max':'100000'},'limits':{'native_ua':100000,'source_budget_ua':100000}})
  files.update({'launch-receipt-private.json':json.dumps(receipt).encode(),'execution-started-private.json':json.dumps(dict(nonce=NONCE,pid=42)).encode(),
   'worker.pid':b'42','config-private.json':json.dumps(config).encode(),'result.json':json.dumps(result).encode()})
  return {'process_state':'absent','receipt':receipt,'files':{n:dict(sha256=h.sha(raw),base64=base64.b64encode(raw).decode()) for n,raw in files.items()}}
 data=envelope()
 def fetch(command,**kw):return subprocess.CompletedProcess('fake-only',0,json.dumps(data).encode(),b'')
 report=h.run('fetch',NONCE,ssh=fetch,private=private)
 assert report['terminal_verified'] and report['result']['passed'] is False and report['result']['restore100_verified'] is False
 assert report['result']['final_observation']['limits']=={'native_ua':100000,'source_budget_ua':100000}
 ok('actual receiver preserves raw/effective source fields; terminal is not restored/passed')
 data=envelope();c=json.loads(base64.b64decode(data['files']['config-private.json']['base64']));c['guard']='/old/r6';raw=json.dumps(c).encode()
 data['files']['config-private.json']={'sha256':h.sha(raw),'base64':base64.b64encode(raw).decode()}
 refuse(lambda:h.run('fetch',NONCE,ssh=fetch,private=private))
 ok('actual receiver rejects R6 guard even in same-nonce R7 envelope')

result=dict(passed=True,cases=len(cases),sequences=cases,tested_files={n:h.sha((HERE/n).read_bytes()) for n in ['host-parent.ps1','host-launcher.py','watch-one-hub.ps1','UsbHubReadOnly.cs']},
 test_source_sha256=h.sha(Path(__file__).read_bytes()),frozen11_or12_suites_rerun=False,transport_calls_are_fake=True,
 device_access=False,usb_access=False,sdk_access=False)
(HERE/'host-migration-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=len(cases),device_access=False,usb_access=False),indent=2))
