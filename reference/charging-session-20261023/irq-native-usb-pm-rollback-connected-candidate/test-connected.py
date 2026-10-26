"""Current cohort connection delta; all device/transport IO stays in temporary models."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load(HERE/'host.py','actual_current_rollback_connected');pins,_=h.source_check()
bt=load(HERE.parent/'irq-native-usb-pm-rollback-host-candidate/test-host.py','current_binding_fixture_definitions')
b=bt.b;w=bt.w;fixture=bt.fixture
encode=bt.b.encode
def save(path,value):path.write_bytes(value if isinstance(value,bytes) else encode(value))
worker_raw=h.local(pins['worker']['path']).read_bytes();sup_raw=(HERE/'supervisor.py').read_bytes()

def fetch_fixture(request,result):
 raw=encode(request);tx=request['transaction_id'];boot=request['identity']['boot_id'];digest=h.sha(raw)
 root='/root/charging-management-20261023/'+tx
 argv=['python3','-B',root+'/restore-worker.py','--execute-rollback'];sargv=['python3','-B',root+'/rollback-supervisor.py','--execute-supervisor']
 common=dict(transaction_id=tx,boot_id=boot,request_sha256=digest)
 process=dict(transaction_id=tx,boot_id=boot,pid=10,start_ticks=100,argv=argv,worker_sha256=request['worker_sha256'])
 launch=dict(common,pid=10,start_ticks=100,argv=argv,supervisor_pid=20)
 end=dict(launch,terminal=True,returncode=0)
 sup=dict(common,pid=20,start_ticks=200,argv=sargv)
 supend=dict(sup,terminal=True,returncode=0,worker_pid=10,worker_returncode=0)
 parent=dict(sup)
 values={'result.json':result,'process-private.json':process,'launch-receipt-private.json':parent,
  'worker-launch-receipt-private.json':launch,'worker-terminal-private.json':end,'supervisor-process-private.json':sup,'supervisor-terminal-private.json':supend}
 files={name:dict(base64=base64.b64encode(encode(value)).decode(),sha256=h.sha(encode(value)),bytes=len(encode(value))) for name,value in values.items()}
 return dict(transaction_id=tx,request_sha256=digest,files=files,worker_terminal_verified=True,worker_terminal=end,
  worker_result=result,process={'state':'absent'},supervisor_process={'state':'absent'})

def remote_fixture(top,request):
 r=load(HERE/'remote.py','current_modeled_remote');fs=Path(top)/request['profile'];fs.mkdir()
 def path(*parts):
  p=Path(*parts);return fs/str(p).lstrip('/') if p.is_absolute() else p
 r.Path=path;r.save=save
 r.os=SimpleNamespace(umask=lambda value:None,geteuid=lambda:0,uname=lambda:SimpleNamespace(version=request['identity']['version']),fsync=os.fsync)
 r.time=SimpleNamespace(CLOCK_BOOTTIME=7,clock_gettime=lambda clock:1000.)
 for name,raw in [('/proc/sys/kernel/random/boot_id',(request['identity']['boot_id']+'\n').encode()),('/sys/devices/soc0/serial_number',b'serial\n'),
  ('/sys/firmware/devicetree/base/compatible',b'realme,samurai\0'),('/etc/samurai-rootfs-release',b'rootfs\n')]:
  p=path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 path('/root/charging-management-20261023').mkdir(parents=True);path('/run').mkdir()
 popens=[]
 def popen(argv,**kwargs):popens.append((argv,kwargs));return SimpleNamespace(pid=810)
 r.subprocess=SimpleNamespace(Popen=popen,DEVNULL=subprocess.DEVNULL,STDOUT=subprocess.STDOUT)
 r.process=lambda receipt,argv:dict(state='alive' if receipt else 'unknown')
 raw=encode(request)
 data=dict(action='launch',request=request,request_sha256=h.sha(raw),request_base64=base64.b64encode(raw).decode(),
  worker_base64=base64.b64encode(worker_raw).decode(),supervisor_base64=base64.b64encode(sup_raw).decode(),supervisor_sha256=h.sha(sup_raw),window_confirmed=True)
 return r,path,popens,data

class ConnectedDelta(unittest.TestCase):
 def test_original_owner_functions_and_three_source_specializations(self):
  old=load(REF/'charging-oem-audit-20261023/rollback-connected-candidate/host.py','original_owner_source')
  def funcs(path):
   text=path.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
  original,current=funcs(Path(old.__file__)),funcs(HERE/'host.py')
  reuse=json.loads((HERE/'source-reuse.json').read_bytes())
  for name in reuse['exact_host_functions']:self.assertEqual(current[name],original[name])
  old_remote=(REF/'charging-oem-audit-20261023/rollback-connected-candidate/remote.py').read_text()
  expected=old_remote.replace('samurai-usb-irq-protection-rollback-request-v1','samurai-irq-native-usb-pm-cold-rollback-request-v1').replace('usb-irq-protection-rollback-','irq-native-usb-pm-rollback-').replace('f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142',pins['worker']['sha256'])
  self.assertEqual((HERE/'remote.py').read_text(),expected)
  compressed=load(h.local(pins['profile']['path']),'actual_original_profile_argv').host_module()
  self.assertEqual(compressed.transport_argv(compressed.PEER),b.transport_argv())

 def test_bound_reaudits_current_cache_and_source_process_observations(self):
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);reviewed,current=bt.source_and_current(w.PROFILES[1]);probe=root/'probe';bt.probe_receipts(probe,reviewed,current)
   tx='irq-native-usb-pm-rollback-bound-fixture'
   with patch.object(h,'PRIVATE',root/'transactions'),patch.object(b,'review_sources',return_value=reviewed):
    actual_loader=h.load_module
    def loader(path,name):return b if name in ['rollback_connected_actual_bind','rollback_connected_launch_reaudit'] else actual_loader(path,name)
    with patch.object(h,'load_module',side_effect=loader):
     h.bind(tx,w.PROFILES[1],root/'stage',root/'fetch',probe);out,_,request,_,_=h.bound(tx,True)
     original=copy.deepcopy(request);binding=json.loads((out/'binding-private.json').read_bytes())
     for field in ['current_cache','source_stage_observations']:
      changed=copy.deepcopy(original)
      if field=='current_cache':changed[field]['instance_inode']+=1
      else:changed[field]['worker']['state']='zombie'
      raw=encode(changed);save(out/'request-private.json',raw);save(out/'binding-private.json',dict(binding,request_sha256=h.sha(raw)))
      with self.assertRaises(ValueError):h.bound(tx,True)
     save(out/'request-private.json',original);save(out/'binding-private.json',binding)
     self.assertEqual(h.bound(tx,False)[2],original)

 def test_remote_three_profiles_exact_request_once_lease_and_cross_boot_fetch(self):
  with tempfile.TemporaryDirectory() as top:
   for profile in w.PROFILES:
    req=fixture.request_for(profile)
    for key,raw in [('serial_sha256',b'serial\n'),('compatible_sha256',b'realme,samurai\0'),('rootfs_sha256',b'rootfs\n')]:
     req['identity'][key]=req['source_identity'][key]=h.sha(raw)
    r,path,popens,data=remote_fixture(top,req);response=r.execute(data)
    root=path('/root/charging-management-20261023')/req['transaction_id']
    self.assertTrue(response['launched']);self.assertEqual(len(popens),1)
    self.assertEqual((root/'request-private.json').read_bytes(),encode(req));self.assertEqual((root/'restore-worker.py').read_bytes(),worker_raw)
    lease=json.loads(path('/run/'+req['transaction_id']+'-window-private.json').read_bytes())
    self.assertEqual(lease['expires_boottime_s']-lease['issued_boottime_s'],120)
    self.assertEqual(lease['boot_id'],req['identity']['boot_id'])
    with self.assertRaises(ValueError):r.execute(data)
    self.assertEqual(len(popens),1)
    path('/proc/sys/kernel/random/boot_id').write_text('99999999-8888-4777-8666-555555555555\n')
    r.process=lambda *args:(_ for _ in ()).throw(AssertionError('old PIDs must not be inspected in another boot'))
    data['action']='fetch';value=r.execute(data)
    self.assertEqual(value['process']['state'],'source_boot_ended');self.assertEqual(value['supervisor_process']['state'],'source_boot_ended')
    self.assertFalse(value['runtime_validation_accepted'])

 def test_fetch_qualifies_actual_two_file_result_not_full_runtime(self):
  with tempfile.TemporaryDirectory() as top:
   for index,profile in enumerate(w.PROFILES):
    req=fixture.request_for(profile);device=fixture.FakeDevice(req);result=w.restore(req,device,True)
    self.assertTrue(result['restored'],result);response=fetch_fixture(req,result)
    out=Path(top)/str(index);out.mkdir();qualified=h.accept_fetch(out,req,encode(req),response)
    self.assertTrue(qualified['rollback_staged_original']);self.assertFalse(qualified['runtime_validation_accepted'])
    self.assertEqual(len(result['final_files']),2);self.assertTrue(result['runtime_pending'])
    bad=copy.deepcopy(result);bad['actual_resident_notes']=dict(w.OLD_NOTES if index else w.NEW_NOTES)
    out=Path(top)/('bad-'+str(index));out.mkdir()
    with self.assertRaises(ValueError):h.accept_fetch(out,req,encode(req),fetch_fixture(req,bad))

 def test_transfer_fixed_compression_once_pending_and_unknown_original_terminal(self):
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);req=fixture.request_for(w.PROFILES[1]);raw=encode(req);(root/'restore-worker.py').write_bytes(worker_raw)
   binding=dict(endpoint=dict(peer=h.PEER,host_key_alias=h.ALIAS,observed_new_boot=req['identity']['boot_id']));events=[]
   def bound(tx,launching=False):events.append(('bound',launching));return root,binding,req,raw,pins
   def start(directory,action,code,argv):
    envelope=ast.literal_eval(ast.parse(code.decode()).body[0].value)
    self.assertEqual(argv[:4],[b.transport_argv()[0],'-C','-6','-T']);self.assertEqual(envelope['request'],req)
    self.assertTrue(code.endswith((HERE/'remote.py').read_bytes()));events.append(('start',action))
    if action=='launch':
     self.assertEqual(base64.b64decode(envelope['worker_base64']),worker_raw)
     return dict(pending=True,job='modeled-original-owner',unknown_means_fetch_only=True)
    out=root/'fetch';out.mkdir();return dict(pending=False,job=str(out),owner_returncode=0)
   with patch.object(h,'bound',side_effect=bound),patch.object(h,'start_job',side_effect=start):
    with self.assertRaises(ValueError):h.transfer('launch',req['transaction_id'],False)
    self.assertFalse((root/'launch-intent-private.json').exists())
    self.assertTrue(h.transfer('launch',req['transaction_id'],True)['pending'])
    with self.assertRaises(ValueError):h.transfer('launch',req['transaction_id'],True)
    self.assertEqual(events.count(('start','launch')),1)
    response=dict(transaction_id=req['transaction_id'],request_sha256=h.sha(raw))
    with patch.object(h,'terminal_job',return_value=(dict(returncode=0),response)),patch.object(h,'accept_fetch',return_value=dict(rollback_staged_original=True)),patch.object(h,'review_launch_transport',side_effect=ValueError('original launch wait unknown')):
     value=h.transfer('fetch',req['transaction_id'])
    self.assertFalse(value['rollback_staged_original']);self.assertFalse(value['original_launch_transport_terminal'])

 def test_probe_owner_existing_readonly_interface_failure_retained_and_no_early_mkdir(self):
  with tempfile.TemporaryDirectory() as top,patch.object(h,'PRIVATE',Path(top)/'private'):
   out=h.PRIVATE/'probe-missing-source'
   with self.assertRaises((OSError,ValueError,RuntimeError,KeyError)):
    h.probe(w.PROFILES[0],Path(top)/'missing-stage',Path(top)/'missing-fetch',out)
   self.assertFalse(h.PRIVATE.exists())
   reviewed,current=bt.source_and_current(w.PROFILES[1]);out=h.PRIVATE/'probe-current-fixture'
   original=h.load_module;events=[]
   def send(path,code):
    events.append(('send',code));temporary=Path(top)/'receipts';bt.probe_receipts(temporary,reviewed,current)
    for item in temporary.iterdir():save(path/item.name,item.read_bytes())
   compressed=SimpleNamespace(host_module=lambda:SimpleNamespace(PEER=b.PEER,transport_argv=lambda peer:b.transport_argv()),send_readonly=send)
   def loader(path,name):
    if name=='current_rollback_connected_probe_bind':return b
    if name=='original_compressed_readonly_owner':return compressed
    return original(path,name)
   with patch.object(h,'load_module',side_effect=loader),patch.object(b,'review_sources',return_value=reviewed):
    value=h.probe(w.PROFILES[1],'modeled-stage','modeled-fetch',out)
    self.assertEqual(value['identity'],current['identity']);self.assertEqual(len(events),1)
    self.assertEqual((out/'executed-device-source.py').read_bytes(),events[0][1])
    failed=h.PRIVATE/'probe-failure-fixture'
    def fail_send(path,code):save(path/'partial-private.txt',b'modeled partial');raise BrokenPipeError('modeled partial transport')
    compressed.send_readonly=fail_send
    with self.assertRaises(BrokenPipeError):h.probe(w.PROFILES[1],'s','f',failed)
    self.assertTrue((failed/'partial-private.txt').exists())
    with self.assertRaises(ValueError):h.probe(w.PROFILES[1],'s','f',failed)

 def test_supervisor_current_schema_regular_request_same_worker_wait(self):
  with tempfile.TemporaryDirectory() as top:
   req=fixture.request_for(w.PROFILES[1]);root=Path(top)/req['transaction_id'];root.mkdir()
   save(root/'request-private.json',req);save(root/'restore-worker.py',worker_raw);save(root/'rollback-supervisor.py',sup_raw)
   save(root/'launch-claim-private.json',dict(transaction_id=req['transaction_id'],request_sha256=h.sha(encode(req)),supervisor_sha256=h.sha(sup_raw)))
   supervisor=load(HERE/'supervisor.py','current_supervisor_schema_test');events=[]
   class Child:
    pid=123
    def wait(self):events.append('wait');return 0
   def popen(argv,**kwargs):
    self.assertEqual(kwargs['stdin'].read(),encode(req));self.assertEqual(argv[-1],'--execute-rollback');events.append('popen');return Child()
   supervisor.subprocess=SimpleNamespace(Popen=popen,STDOUT=subprocess.STDOUT);supervisor.ticks=lambda pid:456
   supervisor.supervise(root)
   self.assertEqual(events,['popen','wait']);self.assertEqual(json.loads((root/'worker-terminal-private.json').read_bytes())['returncode'],0)
   self.assertTrue((root/'supervisor-terminal-private.json').exists())

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ConnectedDelta);result=unittest.TextTestRunner(verbosity=2).run(suite)
 report=dict(passed=result.wasSuccessful(),groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  source_and_device_transport_io_modeled=True,actual_current_binder_profile_inverse_and_worker_result_used=True,
  original_owner_matrix_reused_not_rerun=True,device_accessed=False,actual_runtime_request_created=False,
  files={name:h.sha((HERE/name).read_bytes()) for name in ['host.py','remote.py','supervisor.py','source-pins.json','test-connected.py']})
 save(HERE/'test-result.json',report);raise SystemExit(0 if result.wasSuccessful() else 1)
