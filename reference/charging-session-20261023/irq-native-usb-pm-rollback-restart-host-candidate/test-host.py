"""Current restart wiring only; source/device/process/transport boundaries modeled."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,inspect,json,os,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import sources,proof,controller
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
operator=load(HERE/'fastboot-operator.py','current_restart_operator')
dt=load(HERE.parent/'irq-native-usb-pm-rollback-restart-device-candidate/test-device.py','current_device_fixture_definitions')
w=dt.w;encode=proof.encode
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value if isinstance(value,bytes) else encode(value))
def reviewed(profile=w.PROFILES[1]):
 req,device,result,response,current,guard,raws=dt.review_fixture(profile)
 value=dict(request=req,identity=req['identity'],current=current,rollback=guard['rollback'],post_restore_probe=guard['post_restore_probe'],
  result=result,result_sha256=guard['rollback']['result_sha256'],host_binding_sha256=guard['rollback']['host_binding_sha256'])
 return req,device,response,value
def probe_receipts(path,code,report):
 binder=sources.load('rollback_binder');argv=binder.transport_argv();out=encode(report);empty=b''
 child=dict(pid=123,start_ticks=456,argv=argv,stdin_sha256=proof.sha(code))
 for name,value in [('executed-device-source.py',code),('stdout-private.json',out),('stderr-private.txt',empty),('child-private.json',child),
  ('terminal-private.json',dict(child,terminal=True,returncode=0,stdout_sha256=proof.sha(out),stderr_sha256=proof.sha(empty),primary_error=None,cleanup_errors=[]))]:save(path/name,value)

class RestartHostDelta(unittest.TestCase):
 def test_source_reuse_and_original_only_logdump_inputs(self):
  sources.source_check();base=controller.owner();fb=operator.owner();pins=sources.pins()
  self.assertIn('-C',base.ssh_argv(sources.controller_pins(),dict(kind='usb-ipv6',peer=proof.PEER,host_key_alias='169.254.42.1',original_key_verified=True)))
  for name in ['common.py','proof.py','eud-quiesce.py','eud-restart.py']:
   self.assertEqual((HERE/name).read_bytes(),(HERE.parent/'irq-native-usb-pm-rollback-restart-device-candidate'/name).read_bytes())
  self.assertEqual((HERE/'supervisor.py').read_bytes(),(HERE.parent/'usb-irq-protection-rollback-restart-candidate/supervisor.py').read_bytes())
  def funcs(path):
   text=path.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
  original=funcs(sources.local(pins['baseline']['activation_controller']['path']))
  for name in ['ssh_worker','start_job','terminal_job','reconcile','run','qualify_quiesce','qualify_prepare']:
   self.assertEqual(inspect.getsource(getattr(base,name)).strip(),original[name])
  inputs=fb.local_inputs();self.assertEqual(set(inputs['images']),{'original'});self.assertEqual(set(fb.IMAGES),{'original'})
  self.assertEqual(inputs['unchanged_boot_sha256'],w.BOOT);self.assertEqual(set(fb.IMAGES['original']),{'logdump'})
  self.assertEqual(inputs['images']['original']['logdump'],w.LOGDUMP502)
  self.assertEqual(fb.ACTIONS,('inspect','rollback-original','reboot-original'))
  with self.assertRaises(ValueError):fb.run_action('flash-candidate','modeled',lambda *args:self.fail('must not command'))

 def test_actual_review_completed_uses_distinct_compressed_post_restore_receipts(self):
  req,device,response,value=reviewed();response.update(identity_observation=dict(source_boot_same=True,identity_matches=True),identity_after=dict(source_boot_same=True,identity_matches=True))
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);directory=root/req['transaction_id'];fetch=directory/'fetch-original-private';fetch.mkdir(parents=True);probe=root/'probe';probe.mkdir()
   save(directory/'binding-private.json',{'modeled':True});save(directory/'restore-worker.py',dt.ct.worker_raw);save(fetch/'job-private.json',dict(action='fetch'))
   expected=proof.post_probe_request(req,value['result_sha256'],proof.sha((directory/'binding-private.json').read_bytes()))
   code=('PROBE_REQUEST='+repr(expected)+'\n').encode()+sources.local(sources.pins()['baseline']['current_probe']['path']).read_bytes()
   report=dict(schema=expected['schema'],request=expected,current=value['current'],identity_before=req['identity'],identity_after=req['identity'],
    cache_before=req['current_cache'],cache_after=req['current_cache'],started_boottime_ns=100_000_000_000,ended_boottime_ns=100_000_000_001)
   probe_receipts(probe,code,report);seen=[];original=sources.load
   fake=SimpleNamespace(PRIVATE=root,source_check=lambda:None,bound=lambda *a,**k:(directory,dict(endpoint={'peer':proof.PEER}),req,encode(req),{}),
    terminal_job=lambda path:(dict(returncode=0),response),review_launch_transport=lambda *args:seen.append('original-launch-review'))
   def loader(name):return fake if name=='rollback_host' else original(name)
   with patch.object(sources,'load',side_effect=loader):
    got=proof.review_completed(directory,fetch,probe)
    self.assertEqual(got['current'],value['current']);self.assertEqual(seen,['original-launch-review'])
    self.assertEqual(got['post_restore_probe']['stdin_sha256'],proof.sha(code))
    probe_receipts(probe,code,dict(report,started_boottime_ns=1))
    with self.assertRaises(ValueError):proof.review_completed(directory,fetch,probe)

 def test_six_file_bind_install_and_run_explicit_adapter_private_once(self):
  req,device,response,value=reviewed();base=controller.owner()
  with tempfile.TemporaryDirectory() as top:
   root=Path(top);private=root/'transactions';tx='irq-native-usb-pm-rollback-activate-host-fixture';fs=root/'device-fs';fs.mkdir()
   with patch.object(proof,'review_completed',return_value=value):
    controller.bind(tx,'modeled-rollback','modeled-fetch','modeled-probe',private=private)
    directory,request,_,_=controller.bound(tx,private=private,revalidate=True)
   self.assertEqual(set(request['files']),{'eud-quiesce.py','eud-restart.py','common.py','proof.py','activation-supervisor.py','camera481-expected-private.json'})
   self.assertEqual(base64.b64decode(request['files']['proof.py']['base64']),(HERE/'proof.py').read_bytes())
   remote=load(HERE/'remote.py','actual_new_restart_install');realpath=Path
   def mapped(*args):
    p=realpath(*args);return fs/str(p).lstrip('/') if p.is_absolute() and not p.is_relative_to(root) else p
   for name,raw in [('/proc/mounts',b'tmpfs /run tmpfs rw 0 0\n'),('/proc/sys/kernel/random/boot_id',(request['expected_boot']+'\n').encode())]:save(mapped(name),raw)
   mapped('/run').mkdir(exist_ok=True);remote.OWNER=root/'owner-private.json';calls=[]
   def preflight(actual,path,**kwargs):
    self.assertEqual((path/'common.py').read_bytes(),(HERE/'common.py').read_bytes());calls.append('preflight')
   with patch.object(remote,'Path',side_effect=mapped),patch.object(remote,'preflight',side_effect=preflight):
    missing=copy.deepcopy(request);missing['files'].pop('proof.py')
    with self.assertRaises(ValueError):remote.prepare(missing,root/'bad-install')
    self.assertFalse(remote.OWNER.exists());self.assertTrue(remote.prepare(request,root/'installed')['prepared'])
    self.assertEqual((root/'installed/proof.py').read_bytes(),(HERE/'proof.py').read_bytes())
   starts=[]
   def start(directory,action,actual,pins,endpoint):starts.append((directory,action));return dict(pending=True)
   with patch.object(controller,'PRIVATE',private),patch.object(proof,'review_completed',return_value=value):
    self.assertTrue(controller.run('prepare',tx,True,True,start=start)['pending'])
    with self.assertRaises(ValueError):controller.run('prepare',tx,True,True,start=start)
   self.assertEqual(starts,[(private/tx,'prepare')])

 def test_current_preflight_closes_both_fds_and_keeps_primary_failure(self):
  remote=load(HERE/'remote.py','actual_current_two_fd_preflight')
  with tempfile.TemporaryDirectory() as top:
   root=Path(top)
   for primary in [False,True]:
    for close_error in [False,True]:
     closed=[]
     def close(fd):
      closed.append(fd)
      if close_error and fd==11:raise OSError('modeled first close failure')
     source="from current_restart_cleanup_boundary import os\n_MAC_FD=11\n_SERVICE_FD=12\ndef validate_activation_guard(path,allow_inhibit=False):\n"
     source+=(" raise ValueError('modeled guard failure')\n" if primary else " return {'transaction_id':'t','token':'k','boot_id':'b'},None,None\n")
     save(root/'common.py',source.encode());request=dict(common_sha256=proof.sha(source.encode()),transaction_id='t',token='k',expected_boot='b')
     with patch.dict(sys.modules,{'current_restart_cleanup_boundary':SimpleNamespace(os=SimpleNamespace(close=close))}):
      if primary:
       with self.assertRaisesRegex(ValueError,'modeled guard failure'):remote.preflight(request,root)
      elif close_error:
       with self.assertRaises(RuntimeError):remote.preflight(request,root)
      else:remote.preflight(request,root)
     self.assertEqual(closed,[11,12])

 def test_export_seven_files_consumed_by_current_operator_and_actual_worker(self):
  req,device,response,value=reviewed();base=controller.owner();fb=operator.owner()
  with tempfile.TemporaryDirectory() as top:
   tx='irq-native-usb-pm-rollback-activate-context-fixture';directory=Path(top)/tx;directory.mkdir();token='a'*48
   guard=proof.make_guard(tx,token,value);save(directory/'guard-private.json',guard)
   save(directory/'binding-private.json',dict(rollback_directory='r',rollback_fetch_directory='f',post_restore_probe_directory='p'))
   ident=dict(transaction_id=tx,token=token,boot_id=guard['boot_id']);remote='/root/charging-management-20261023/'+tx
   qargv=['python3','-B',remote+'/eud-quiesce.py','--guard',remote+'/guard-private.json','--commit-quiesce']
   rargv=['python3','-B',remote+'/eud-restart.py','--guard',remote+'/guard-private.json','--commit-restart2-bootloader']
   for name,raw in [('quiesce-state-private.json',dict(ident,pid=301,terminal=True,exit_code=0)),('quiesce-summary-private.json',dict(ident,taint=0)),
    ('quiesce-boot-id-private.txt',(guard['boot_id']+'\n').encode()),('quiesce-process-private.json',dict(ident,pid=301,startticks=401,argv=qargv,status='absent')),
    ('restart-claim-private.json',dict(ident,schema='samurai-eud-restart-host-claim-v1',guard_sha256=proof.sha(encode(guard)),request_count=1,worker_sha256=sources.worker_hashes()['eud-restart.py'],argv=rargv)),
    ('restart-job-private.json',dict(job='modeled-original-job'))]:save(directory/name,raw)
   terminal=dict(pid=302,startticks=402,argv=['modeled-original-ssh'],terminal=True,returncode=255)
   with patch.object(base,'terminal_job',return_value=(terminal,b'')),patch.object(proof,'review_completed',return_value=value):
    context=controller.export_context(directory);path=directory/'host-context-private.json'
    self.assertEqual(operator.validate_context(path),context);self.assertEqual(len(context['files']),7)
    action=directory/'fastboot-operator/inspect';action.mkdir(parents=True);inputs=fb.local_inputs()
    claim=dict(schema='samurai-irq-native-usb-pm-fastboot-action-v1',execute_authorized=True,window_confirmed=True,action='inspect',
     transaction_id=tx,token=token,old_boot_id=guard['boot_id'],context_path=str(path),context_sha256=fb.sha(path),operator_sha256=fb.sha(HERE/'fastboot-operator.py'),inputs=inputs,claimed_ns=100)
    save(action/'request-private.json',claim);serial=fb.read_json(fb.IDENTITY)['serial'];commands=[]
    def command(directory,label,argv):
     commands.append(label)
     if label=='devices':return serial+'\tfastboot\n',''
     if label=='product':return '','product: msmnile\n'
     part=label[:-5];return '',f'partition-size:{part}: {fb.SIZES[part]}\n'
    with patch.object(fb,'command',side_effect=command):fb.worker(action/'request-private.json')
    result=json.loads((action/'result-private.json').read_bytes());self.assertTrue(result['passed'],result)
    self.assertEqual(commands,['devices','product','boot-size','logdump-size'])
    bad=copy.deepcopy(context);bad['schema']='legacy';save(path,bad)
    with self.assertRaises(ValueError):operator.validate_context(path)

 def test_probe_owner_partial_retention_and_worker_dispatch(self):
  req,device,response,value=reviewed();code=b'# modeled authenticated post-restore program\n';sent=[];original=sources.load
  fake=SimpleNamespace(host_module=lambda:SimpleNamespace(PEER=proof.PEER,transport_argv=lambda peer:sources.load('rollback_binder').transport_argv()),
   send_readonly=lambda out,raw:(sent.append(raw),save(out/'actual-input-private.py',raw)))
  def loader(name):return fake if name=='compressed_profile' else original(name)
  with tempfile.TemporaryDirectory() as top,patch.object(controller,'PRIVATE',Path(top)/'private'),patch.object(sources,'load',side_effect=loader):
   out=controller.PRIVATE/'probe-current-fixture'
   with patch.object(controller,'probe_payload',return_value=code),patch.object(proof,'review_completed',return_value=value):
    self.assertEqual(controller.probe('r','f',out),value);self.assertEqual(sent,[code])
    with self.assertRaises(ValueError):controller.probe('r','f',out)
   bad=controller.PRIVATE/'probe-partial-fixture'
   def failure(out,raw):save(out/'partial-private.txt',b'partial');raise BrokenPipeError('modeled partial')
   fake.send_readonly=failure
   with patch.object(controller,'probe_payload',return_value=code):
    with self.assertRaises(BrokenPipeError):controller.probe('r','f',bad)
   self.assertTrue((bad/'partial-private.txt').exists())
  with patch.object(controller.owner(),'ssh_worker') as run,patch.object(sys,'argv',['controller.py','_ssh-worker','--job','modeled-job']):
   controller.main();run.assert_called_once_with('modeled-job')
  with patch.object(operator.owner(),'worker') as run,patch.object(sys,'argv',['fastboot-operator.py','--_worker','modeled-request']):
   operator.main();run.assert_called_once_with('modeled-request')

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(RestartHostDelta);result=unittest.TextTestRunner(verbosity=2).run(suite)
 report=dict(passed=result.wasSuccessful(),groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  source_device_transport_process_io_modeled=True,actual_current_proof_profile_and_original_saved_transport_used=True,
  actual_original_worker_inspect_with_modeled_commands=True,device_accessed=False,actual_runtime_request_created=False,old_matrices_rerun=False,
  files={name:proof.sha((HERE/name).read_bytes()) for name in ['test-host.py','controller.py','fastboot-operator.py','remote.py','sources.py','source-pins.json']})
 save(HERE/'test-result.json',report);raise SystemExit(0 if result.wasSuccessful() else 1)
