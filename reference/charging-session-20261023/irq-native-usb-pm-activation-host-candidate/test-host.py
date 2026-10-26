"""Only current controller binding/export and new two-fd preflight boundaries."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,tempfile,unittest
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
c=load(HERE/'controller.py','current_pm_activation_host')
r=load(HERE/'remote.py','current_pm_activation_remote')
d=load(c.WORKERS/'test-delta.py','current_stage_fixture_definitions_only')
sha=c.sha
old=HERE.parent/'usb-irq-protection-activation-host-candidate'
def function(path,name):
 source=path.read_text();return ast.get_source_segment(source,next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name))
fixture_ns={'c':c,'HERE':HERE,'Path':Path,'json':json,'base64':base64,'sha':sha}
for name in ['job','quiesce_facts']:exec(function(old/'test-host.py',name),fixture_ns)
def job(directory,action,request,rc=0):
 target=fixture_ns['job'](directory,action,request,rc=rc)
 terminal=target/'ssh-terminal-private.json'
 c.save(target/'ssh-finalization-private.json',dict(pid=201,stdin_sha256=c.load_json(target/'job-private.json')['program_sha256'],
  wait_returned=True,cleanup_errors={},terminal_publish_error=None,cleanup_passed=True,terminal_sha256=sha(terminal.read_bytes())))
 return target

class CurrentHost(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.top=Path(self.temp.name)
  root,_,meta,_,_,_,_,_=d.actual_stage_fixture(self.top)
  self.stage=root;self.tx='irq-native-usb-pm-activate-host-fixture';self.private=self.top/'activation'
  identity=d.request['identity'];adoption=d.request['adoption']
  self.endpoint=dict(kind='usb-ipv6',peer='fe80::62:bcff:fe28:a101%29',interface_index=29,host_key_alias='169.254.42.1',
   original_key_verified=True,observed_new_boot=identity['boot_id'],guard_path=adoption['guard_path'],
   postboot_Image502_passed=True,postboot_USB_IRQ_protection_passed=True)
  raw=(json.dumps({'endpoint':self.endpoint},indent=2)+'\n').encode();(root/'binding-private.json').write_bytes(raw)
  projection=copy.deepcopy(meta['stage']);projection['host_binding_sha256']=sha(raw)
  self.review=dict(schema='samurai-irq-native-usb-pm-stage-review-v1',stage=projection,request=d.request,
   source_review_inputs={'fixture':'separately tested current stage proof'},
   source_runtime=dict(manifest_sha256=c.load_json(c.WORKERS/'prepare-contract.json')['fixed_guard_fields']['source_manifest_sha256'],
    boot_id=identity['boot_id'],guard_path=adoption['guard_path'],guard_sha256=adoption['guard_sha256'],endpoint=self.endpoint))
  self.projection=projection
 def tearDown(self):self.temp.cleanup()
 def bind(self):
  with patch.object(c,'reviewed',return_value=(self.review,self.projection)):
   c.bind(self.tx,self.stage,self.stage/'fetch-fixture',private=self.private)
  directory=self.private/self.tx;return directory,c.load_json(directory/'request-private.json')

 def test_current_stage_and_endpoint_bind_then_revalidate_same_guard(self):
  directory,request=self.bind();guard=c.load_json(directory/'guard-private.json')
  self.assertEqual(guard['partitions'],['logdump']);self.assertTrue(guard['source_kernel_version'].startswith('#502 '));self.assertTrue(guard['kernel_version'].startswith('#504 '))
  self.assertEqual(guard['adoption'],d.request['adoption']);self.assertEqual(guard['stage'],self.projection)
  self.assertEqual(set(request['files']),{'eud-quiesce.py','eud-restart.py','common.py','camera481-expected-private.json','activation-supervisor.py'})
  with patch.object(c,'reviewed',return_value=(self.review,self.projection)):
   self.assertEqual(c.bound(self.tx,private=self.private,revalidate=True)[1],request)
   with self.assertRaises(ValueError):c.bind(self.tx,self.stage,'same',private=self.private)
  self.assertFalse((directory/'prepare-intent-private.json').exists())
  pins=c.source_check();self.assertEqual(c.ssh_argv(pins,self.endpoint)[1:4],['-C','-6','-T'])

 def test_bad_source_or_endpoint_rejected_before_binding_directory(self):
  missing=self.top/'never-created'
  with patch.object(c,'reviewed',side_effect=FileNotFoundError('missing actual stage originals')):
   with self.assertRaises(FileNotFoundError):c.bind(self.tx,self.stage,'missing',private=missing)
  self.assertFalse(missing.exists())
  bad=copy.deepcopy(self.review);bad['request']['identity']['version']='#504 wrong source'
  with patch.object(c,'reviewed',return_value=(bad,self.projection)):
   with self.assertRaises(ValueError):c.bind(self.tx,self.stage,'missing',private=missing)
  self.assertFalse(missing.exists())
  (self.stage/'binding-private.json').write_bytes(b'changed original endpoint')
  with patch.object(c,'reviewed',return_value=(self.review,self.projection)):
   with self.assertRaises(ValueError):c.bind(self.tx,self.stage,'missing',private=missing)
  self.assertFalse(missing.exists())

 def test_same_original_pending_intent_never_dispatched_twice(self):
  directory,request=self.bind();calls=[]
  def start(*args):calls.append(args[1]);return dict(pending=True,job='original-pending',no_replay=True)
  with patch.object(c,'reviewed',return_value=(self.review,self.projection)):
   first=c.run('prepare',self.tx,True,True,private=self.private,start=start)
   self.assertTrue(first['pending'])
   with self.assertRaises(ValueError):c.run('prepare',self.tx,True,True,private=self.private,start=start)
  self.assertEqual(calls,['prepare']);self.assertEqual(c.load_json(directory/'prepare-intent-private.json')['request_count'],1)

 def test_preflight_closes_both_own_fds_on_success_failure_and_close_error(self):
  root=self.top/'preflight';root.mkdir();source=b'# inert modeled guard\n';(root/'common.py').write_bytes(source)
  request={'transaction_id':self.tx,'token':'a'*48,'expected_boot':'fixture-boot','common_sha256':sha(source)}
  for health_error,close_error in [(False,False),(True,False),(False,True),(True,True)]:
   calls=[];states=[]
   def close(fd):
    calls.append(fd)
    if close_error and fd==72:raise OSError('modeled MAC-fd close failed')
   def execute(code,ns):
    def validate(*args,**kw):
     if health_error:raise ValueError('modeled guard health changed')
     return dict(transaction_id=self.tx,token='a'*48,boot_id='fixture-boot'),None,None
    ns.update(_MAC_FD=72,_SERVICE_FD=71,os=SimpleNamespace(close=close),validate_activation_guard=validate);states.append(ns)
   with patch.object(r,'exec',side_effect=execute,create=True):
    if health_error or close_error:
     with self.assertRaises(ValueError if health_error else RuntimeError):r.preflight(request,root)
    else:self.assertEqual(r.preflight(request,root)[0]['transaction_id'],self.tx)
   self.assertEqual(calls,[72,71]);self.assertIsNone(states[0]['_MAC_FD']);self.assertIsNone(states[0]['_SERVICE_FD'])

 def test_actual_export_to_current_logdump_operator_preserves_ssh255_as_unknown(self):
  directory,request=self.bind();job(directory,'quiesce',request,255)
  target,value,_=fixture_ns['quiesce_facts'](directory,request);c.qualify_quiesce(directory,value,target)
  remote='/root/charging-management-20261023/'+self.tx
  c.save(directory/'restart-claim-private.json',dict(schema='samurai-eud-restart-host-claim-v1',transaction_id=self.tx,token=request['token'],
   boot_id=request['expected_boot'],guard_sha256=request['guard_sha256'],request_count=1,worker_sha256=c.WORKER_HASHES['eud-restart.py'],
   argv=['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader']))
  job(directory,'restart',request,255);started=[]
  def unavailable(*args):
   started.append(args[1]);self.assertTrue((directory/'host-context-private.json').exists());return dict(pending=True,no_replay=True)
  c.run('status',self.tx,True,True,private=self.private,start=unavailable)
  self.assertEqual(started,['status']);context=c.load_json(directory/'host-context-private.json')
  self.assertEqual(context['source_review_inputs'],self.review['source_review_inputs'])
  operator=load(c.WORKERS/'fastboot-operator.py','actual_current_logdump_export_gate')
  proof=SimpleNamespace(review_stage=lambda *args:self.review,guard_stage_fields=lambda review:self.projection)
  spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
  with patch('importlib.util.spec_from_file_location',return_value=spec),patch('importlib.util.module_from_spec',return_value=proof):
   self.assertEqual(operator.validate_context(directory/'host-context-private.json'),context)
  dispatch=c.load_json(directory/'restart-dispatch-private.json')
  self.assertEqual(dispatch['host_process']['returncode'],255);self.assertFalse(dispatch['syscall_success_proven'])

 def test_original_r2_ownership_and_unchanged_device_supervisor_reused(self):
  reuse=c.load_json(HERE/'source-reuse.json')
  for name in reuse['unchanged_controller_functions']:
   self.assertEqual(function(old/'controller.py',name),function(HERE/'controller.py',name))
  for name in reuse['unchanged_remote_functions']:
   self.assertEqual(function(old/'remote.py',name),function(HERE/'remote.py',name))
  self.assertEqual((old/'supervisor.py').read_bytes(),(HERE/'supervisor.py').read_bytes())
  self.assertEqual(len(reuse['unchanged_controller_functions']),23)
  self.assertTrue({'ssh_worker','terminal_job','start_job','run'}.issubset(reuse['unchanged_controller_functions']))

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CurrentHost))
 report=dict(passed=result.wasSuccessful(),methods=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  synthetic_stage_and_device_process_boundaries=True,actual_export_current_operator_function_used=True,
  device_accessed=False,actual_runtime_binding_created=False,old_R1_R2_matrices_rerun=False,
  tested_files={name:sha((HERE/name).read_bytes()) for name in ['controller.py','remote.py','supervisor.py','prepare.py','source-pins.json','test-host.py']})
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
