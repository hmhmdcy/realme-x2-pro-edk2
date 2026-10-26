"""Only new transport/identity binding and retained once-only dispatch edges."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,datetime,hashlib,importlib.util,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('r8_usb500_host',HERE/'host-launcher.py')
old=load('r7_usb500_host',HERE.parents[1]/'charging-oem-audit-20261023/usb500-r7-candidate/host-launcher.py')
cases=[]
assert h.REMOTE_FETCH==old.REMOTE_FETCH
assert h.REMOTE_LAUNCH[h.REMOTE_LAUNCH.index("argv=['python3'"):]==old.REMOTE_LAUNCH[old.REMOTE_LAUNCH.index("argv=['python3'"):]
cases.append('actual original remote Popen receipt and fetch programs unchanged')
with tempfile.TemporaryDirectory(prefix='usb500-r8-host-') as td:
 p=Path(td)
 for name in [h.BASELINE_REL,h.ENDPOINT_REL,'boot-adoption-private.json']:
  target=p/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((h.PRIVATE/name).read_bytes())
 calls=[]
 def raw(command,**kw):calls.append(command);return subprocess.CompletedProcess('fake',0,b'{}',b'')
 fake=SimpleNamespace(raw_ssh=raw)
 with patch.object(h,'PRIVATE',p),patch.object(h.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))),patch.object(h.importlib.util,'module_from_spec',return_value=fake):
  route=h.transport();route('fixture-read',timeout=3)
  assert len(calls)==2 and calls[0].endswith(h.GUARD) and calls[1]=='fixture-read'
  with patch.object(h,'TRANSPORT_SHA','0'*64):
   try:h.transport()
   except ValueError:pass
   else:raise AssertionError('old transport accepted')
 cases.append('actual new pinned-key helper hash and new boot guard checked before fake action; no fallback')
 now=datetime.datetime.now(datetime.timezone.utc)
 nonce='a'*48
 gate={'owned_handle_checked':True,'host_trigger_utc':now.isoformat(),'host_ready':{
  'armed':True,'target_port':16,'remaining_seconds_at_trigger':120,'decoder_sha256':h.DECODER,'collector_sha256':h.COLLECTOR,
  'host_worker_pid':123,'capture_id':'usb500-r8-eud-off-'+nonce,'ready_at_utc':now.isoformat()}}
 gp=p/'gate.json';gp.write_text(json.dumps(gate));sent=[]
 def unknown(command,**kw):sent.append(json.loads(kw['input']));raise subprocess.TimeoutExpired('fake-only',30)
 for attempt in [0,1]:
  try:h.run('launch',nonce,gp,True,ssh=unknown,private=p)
  except (subprocess.TimeoutExpired,FileExistsError):pass
  else:raise AssertionError('unknown or replay accepted')
 assert len(sent)==1 and sent[0]['guard']==h.GUARD and sent[0]['manifest_sha256']==h.MANIFEST
 cases.append('actual unknown new-profile launch retains durable original request and refuses second dispatch')
assert h.check_local()['checked_local_only']
cases.append('actual default check-local validates new R3/hash/programs without transport or USB')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'passed':True,'cases':len(cases),'sequences':cases,
 'tested_files':{n:sha(HERE/n) for n in ['host-launcher.py','host-parent.ps1','watch-one-hub.ps1','UsbHubReadOnly.cs']},
 'test_source_sha256':sha(Path(__file__)),'transport_calls_fake':True,'device_access':False,'usb_access':False,'old_suites_rerun':False}
(HERE/'host-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_cases':len(cases),'device_access':False,'usb_access':False}))
