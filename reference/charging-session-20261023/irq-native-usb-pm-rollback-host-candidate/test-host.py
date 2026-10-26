"""Affected saved-action/current-probe/binding paths; no transport is launched."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,inspect,json,tempfile,unittest,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=__import__('importlib.util',fromlist=['x'])
def load(path,name):
 s=spec.spec_from_file_location(name,path);m=spec.module_from_spec(s);s.loader.exec_module(m);return m
b=load(HERE/'bind.py','current_rollback_binding_test')
s=load(HERE/'saved-proof.py','current_rollback_saved_test')
p=load(HERE/'current-probe.py','current_rollback_probe_test')
fixture=load(HERE.parent/'irq-native-usb-pm-cold-rollback-candidate/test-rollback.py','old_rollback_fixture_definitions_only')
w=fixture.m
def save(path,value):
 raw=value if isinstance(value,bytes) else b.encode(value);path.write_bytes(raw);return b.sha(raw)

def source_and_current(profile):
 request=fixture.request_for(profile);expected=w.expected_profile(request)
 reviewed=dict(profile=profile,source_identity=request['source_identity'],source_stage={'synthetic':True},
  source_stage_observations={'worker':{'state':'absent'},'supervisor':{'state':'absent'}},activation=request['activation'])
 current=dict(identity=request['identity'],release=w.RELEASE,machine='aarch64',taint='0',
  notes=copy.deepcopy(expected['notes']),module_states={name:'live' for name in expected['notes']},
  boot=dict(bytes=100663296,sha256=w.BOOT),logdump=dict(bytes=67108864,sha256=expected['logdump']),current_cache=request['current_cache'])
 return reviewed,current

def probe_receipts(directory,reviewed,current,mutate=None):
 request=b.probe_request(reviewed,b.PEER);payload=('PROBE_REQUEST='+repr(request)+'\n').encode()+(HERE/'current-probe.py').read_bytes()
 report=dict(schema=request['schema'],request=request,identity_before=current['identity'],identity_after=current['identity'],
  current=current,cache_before=current['current_cache'],cache_after=current['current_cache'],started_boottime_ns=10,ended_boottime_ns=11)
 # Real JSON observations are independent values, not shared Python fixture aliases.
 report=json.loads(json.dumps(report))
 if mutate:mutate(report)
 directory.mkdir();save(directory/'executed-device-source.py',payload)
 out=b.encode(report);save(directory/'stdout-private.json',out);save(directory/'stderr-private.txt',b'')
 child=dict(pid=123,start_ticks=456,argv=b.transport_argv(),stdin_sha256=b.sha(payload))
 save(directory/'child-private.json',child)
 save(directory/'terminal-private.json',dict(child,terminal=True,returncode=0,stdout_sha256=b.sha(out),stderr_sha256=b.sha(b''),primary_error=None,cleanup_errors=[]))

def context_fixture(top):
 operator=s.load_module(s.source_check()['operator']['path'],'actual_operator_fixture')
 tx='irq-native-usb-pm-activate-host-fixture';root=Path(top)/tx;root.mkdir()
 identity=copy.deepcopy(fixture.source);token='a'*48;boot=identity['boot_id'];remote='/root/charging-management-20261023/'+tx
 stage=dict(stage={'synthetic':True},source_review_inputs={'modeled_retained_source':True},request=dict(identity=identity,adoption={'synthetic':True}))
 contract=operator.read_json(operator.ACTIVATION/'prepare-contract.json')
 guard=dict(contract['fixed_guard_fields'],transaction_id=tx,token=token,boot_id=boot,soc_serial_sha256=identity['serial_sha256'],
  compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'],stage=stage['stage'],adoption=stage['request']['adoption'])
 def entry(name,value):return dict(path=name,sha256=save(root/name,value))
 common=dict(transaction_id=tx,token=token,boot_id=boot)
 qargv=['python3','-B',remote+'/eud-quiesce.py','--guard',remote+'/guard-private.json','--commit-quiesce']
 rargv=['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader']
 files=dict(guard=entry('guard-private.json',guard),quiesce_state=entry('state-private.json',dict(common,pid=111,terminal=True,exit_code=0)),
  quiesce_summary=entry('summary.json',dict(common,taint=0)),quiesce_boot_id=entry('boot-id-private.txt',(boot+'\n').encode()),
  quiesce_process=entry('process-private.json',dict(common,pid=111,startticks=123,argv=qargv,status='absent')))
 claim=dict(common,schema='samurai-eud-restart-host-claim-v1',guard_sha256=files['guard']['sha256'],request_count=1,
  worker_sha256=operator.pinned_tools()['eud-restart.py'],argv=rargv)
 files['restart_claim']=entry('restart-claim-private.json',claim)
 files['restart_dispatch']=entry('restart-dispatch-private.json',dict(claim,schema='samurai-eud-restart-dispatch-v1',
  host_claim_sha256=files['restart_claim']['sha256'],state='dispatched_once',restart_claim_intent='claimed_by_pinned_worker',
  host_process=dict(pid=222,startticks=456,argv=['ssh','modeled'],terminal=True,returncode=255)))
 stage_directory=root/'source-stage';fetch=root/'source-fetch';fetch.mkdir()
 save(fetch/'received-result-private.json',dict(process={'state':'absent'},supervisor_process={'state':'absent'}))
 context=dict(schema='samurai-irq-native-usb-pm-fastboot-context-v1',transaction_id=tx,token=token,old_boot_id=boot,
  guard_sha256=files['guard']['sha256'],files=files,stage_directory=str(stage_directory),stage_fetch_directory=str(fetch),source_review_inputs=stage['source_review_inputs'])
 path=root/'host-context-private.json';save(path,context)
 adapted=s.operator_for_past_context(stage,stage_directory,fetch)
 return path,context,stage,adapted

def action_receipts(path,context,operator,action,when):
 inputs=operator.local_inputs();serial=operator.read_json(operator.IDENTITY)['serial']
 directory=path.parent/'fastboot-operator'/action;directory.mkdir(parents=True)
 def call(label,argv):
  if label=='devices':out,err=serial+'\tfastboot\n',''
  elif label=='product':out,err='','product: msmnile\n'
  elif label.endswith('-size'):
   part=label[:-5];out,err='',f'partition-size:{part}: {operator.SIZES[part]}\n'
  elif label=='flash-logdump':out,err='',"Writing 'logdump' OKAY\n"
  elif label=='reboot':out,err='',''
  else:raise AssertionError(label)
  save(directory/(label+'-command-private.json'),dict(requested_argv=argv,request_count=1))
  save(directory/(label+'-process-private.json'),dict(pid=100,requested_argv=argv,observed=dict(pid=100,startticks=200,argv=['modeled-child'])))
  save(directory/(label+'-stdout-private.bin'),out.encode());save(directory/(label+'-stderr-private.bin'),err.encode())
  save(directory/(label+'-terminal-private.json'),dict(pid=100,requested_argv=argv,terminal=True,returncode=0,
   stdout_sha256=b.sha(out.encode()),stderr_sha256=b.sha(err.encode())))
  return out,err
 result=operator.run_action(action,serial,call)
 request=dict(schema='samurai-irq-native-usb-pm-fastboot-action-v1',execute_authorized=True,window_confirmed=True,
  action=action,operator_sha256=s.sha(s.OPERATOR_PATH),inputs=inputs,claimed_ns=when,transaction_id=context['transaction_id'],
  token=context['token'],old_boot_id=context['old_boot_id'],context_sha256=s.sha(path))
 if action in operator.REBOOT_IMAGES:request['image_binding']=operator.reboot_binding(path.parent/'fastboot-operator',action)
 save(directory/'request-private.json',request);save(directory/'result-private.json',dict(request,**result,terminal=True,passed=True,commands_terminal=True))
 return directory

class HostDelta(unittest.TestCase):
 def test_exact_reused_functions_and_default_no_dispatch(self):
  pins=b.source_check();old=s.load_module(pins['completion_method']['path'],'original_completion_source')
  self.assertEqual(inspect.getsource(s.saved_command),inspect.getsource(old.saved_command))
  expected=inspect.getsource(old.review_action).replace('samurai-usb-irq-protection-fastboot-action-v1','samurai-irq-native-usb-pm-fastboot-action-v1')
  # The pinned old reviewer names its operator through HERE.
  expected=expected.replace("HERE/'fastboot-operator.py'",'OPERATOR_PATH')
  self.assertEqual(inspect.getsource(s.review_action),expected)
  self.assertEqual(inspect.getsource(p.ProbeIdentity.identity),inspect.getsource(w.Device.identity))
  self.assertEqual(inspect.getsource(p.ProbeCarriers.current),inspect.getsource(w.BaseDevice.current))
  for name in ['bind.py','saved-proof.py','current-probe.py','shared.py']:
   tree=ast.parse((HERE/name).read_text())
   self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen' for n in ast.walk(tree)))

 def test_probe_brackets_close_on_success_failure_and_partial_open(self):
  reviewed,current=source_and_current(w.PROFILES[1]);request=b.probe_request(reviewed,b.PEER)
  class Device:
   def __init__(self,mode):self.closed=False;self.mode=mode;self.calls=0
   def identity(self):return copy.deepcopy(current['identity'])
   def open_cache(self):
    if self.mode=='partial':raise OSError('modeled partial open')
   def cache_evidence(self):
    self.calls+=1;value=copy.deepcopy(current['current_cache'])
    if self.mode=='changed' and self.calls==3:value['instance_inode']+=1
    return value
   def current(self,request):return copy.deepcopy(current)
   def close(self):self.closed=True
  for mode in ['good','changed','partial']:
   device=Device(mode)
   if mode=='good':self.assertEqual(p.collect(request,device)['current'],current)
   else:
    with self.assertRaises((RuntimeError,OSError)):p.collect(request,device)
   self.assertTrue(device.closed)

 def test_three_profiles_authenticate_actual_receipts_and_bind_exact_inverse(self):
  with tempfile.TemporaryDirectory() as top:
   for index,profile in enumerate(w.PROFILES):
    reviewed,current=source_and_current(profile);directory=Path(top)/str(index)
    probe_receipts(directory,reviewed,current)
    with patch.object(b,'review_sources',return_value=reviewed):
     output=Path(top)/('bound-'+str(index));result=b.bind(output,'irq-native-usb-pm-rollback-host-fixture',profile,'modeled-stage','modeled-fetch',directory)
    request=json.loads((output/'request-private.json').read_bytes());self.assertEqual(request['current_cache'],current['current_cache'])
    self.assertEqual(request['source_stage_observations'],reviewed['source_stage_observations'])
    self.assertEqual(set(w.unpack(request)),set(w.OLD_FILES));self.assertFalse(result['worker_launched'])
    self.assertFalse(result['lease_written']);self.assertEqual(result['identity'],current['identity'])
    self.assertEqual((output/'restore-worker.py').read_bytes(),b.local(b.source_check()['worker']['path']).read_bytes())

 def test_wrong_current_cache_kernel_carrier_and_terminal_refused(self):
  reviewed,current=source_and_current(w.PROFILES[1])
  mutations=[lambda r:r['current']['logdump'].update(sha256=w.LOGDUMP502),lambda r:r['current']['notes'].update(w.OLD_NOTES),
   lambda r:r['cache_after'].update(instance_inode=999),lambda r:r['identity_after'].update(boot_id=fixture.source['boot_id']),
   lambda r:r['request'].update(saved_source_binding_sha256='0'*64),lambda r:r.update(ended_boottime_ns=1)]
  with tempfile.TemporaryDirectory() as top,patch.object(b,'review_sources',return_value=reviewed):
   for index,mutate in enumerate(mutations):
    directory=Path(top)/str(index);probe_receipts(directory,reviewed,current,mutate)
    with self.assertRaises((RuntimeError,ValueError)):b.review_current(w.PROFILES[1],'s','f',directory)
   for index,field in enumerate(['argv','stdin_sha256','returncode','cleanup_errors']):
    directory=Path(top)/('terminal-'+str(index));probe_receipts(directory,reviewed,current)
    terminal=json.loads((directory/'terminal-private.json').read_bytes())
    terminal[field]={'argv':['untrusted'],'stdin_sha256':'0'*64,'returncode':255,'cleanup_errors':['unknown']}[field]
    save(directory/'terminal-private.json',terminal)
    with self.assertRaises(ValueError):b.review_current(w.PROFILES[1],'s','f',directory)

 def test_past_context_preserves_seven_files_and_actual_source_gate(self):
  with tempfile.TemporaryDirectory() as top:
   path,context,stage,operator=context_fixture(top)
   self.assertEqual(operator.validate_context(path),context)
   bad=copy.deepcopy(context);bad['source_review_inputs']={'wrong':True};save(path,bad)
   with self.assertRaises(ValueError):operator.validate_context(path)
   save(path,context);(path.parent/'summary.json').write_text('{}')
   with self.assertRaises(ValueError):operator.validate_context(path)

 def test_original_action_replay_two_pairs_and_unknown_actions(self):
  for profile,pair in [(w.PROFILES[1],['flash-candidate','reboot-candidate']),(w.PROFILES[2],['rollback-original','reboot-original'])]:
   with tempfile.TemporaryDirectory() as top:
    path,context,stage,operator=context_fixture(top)
    directory=action_receipts(path,context,operator,pair[0],100);action_receipts(path,context,operator,pair[1],200)
    original_loader=s.load_module
    def loader(path_arg,name):
     if name=='actual_retained_source_reviewer':return SimpleNamespace(review_retained_stage=lambda *args:dict(stage_review=stage))
     return original_loader(path_arg,name)
    with patch.object(s,'load_module',side_effect=loader):
     value=s.review_profile_sources(profile,context['stage_directory'],context['stage_fetch_directory'],path)
     self.assertEqual(value['activation']['action_pair'],pair);self.assertFalse(value['current_identity_or_health_verified'])
     terminal=directory/'flash-logdump-terminal-private.json';saved=json.loads(terminal.read_bytes());save(terminal,dict(saved,returncode=255))
     with self.assertRaises(ValueError):s.review_profile_sources(profile,context['stage_directory'],context['stage_fetch_directory'],path)
     save(terminal,saved);opposing='rollback-original' if profile==w.PROFILES[1] else 'flash-candidate'
     (path.parent/'fastboot-operator'/opposing).mkdir()
     with self.assertRaises(ValueError):s.review_profile_sources(profile,context['stage_directory'],context['stage_fetch_directory'],path)

 def test_missing_actual_stage_rejected_before_any_binding_output(self):
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);output=root/'must-not-exist'
   with self.assertRaises((OSError,ValueError,RuntimeError,KeyError)):
    b.bind(output,'irq-native-usb-pm-rollback-host-fixture',w.PROFILES[0],root/'missing-stage',root/'missing-fetch',root/'missing-probe')
   self.assertFalse(output.exists())

if __name__=='__main__':
 suite=(unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:],HostDelta) if sys.argv[1:] else unittest.defaultTestLoader.loadTestsFromTestCase(HostDelta))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 report=dict(passed=result.wasSuccessful(),groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  saved_source_and_device_io_modeled=True,actual_old_transport_authenticator_used=True,actual_profile_and_inverse_unpack_used=True,
  actual_runtime_request_created=False,device_accessed=False,old_matrices_rerun=False,
  files={name:b.sha((HERE/name).read_bytes()) for name in ['test-host.py','bind.py','saved-proof.py','current-probe.py','shared.py']})
 save(HERE/'test-result.json',report);raise SystemExit(0 if result.wasSuccessful() else 1)
