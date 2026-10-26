"""Current recovery record/cache/profile delta; no hardware or transport."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,sys,tempfile,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import sources
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load(HERE/'proof.py','actual_current_restart_proof');c=load(HERE/'common.py','actual_current_restart_common')
ct=load(HERE.parent/'irq-native-usb-pm-rollback-connected-candidate/test-connected.py','current_connection_fixture_definitions')
w=ct.w;fixture=ct.fixture;encode=p.encode
def file_entry(raw):return dict(base64=base64.b64encode(raw).decode(),sha256=p.sha(raw),bytes=len(raw))
def model(profile,*,full=False,fault=False):
 req=fixture.request_for(profile);device=fixture.FakeDevice(req,stopped=not full,full=full)
 if fault:device.observation['sample'].update(latched=1,cycle_timeout=1,error=-110)
 result=w.restore(req,device,True);assert result['restored'],result
 response=ct.fetch_fixture(req,result)
 for role,pid in [('process',10),('supervisor_process',20)]:response[role]['pid']=pid
 for name in ['before-private.json','stopped-private.json','after-private.json']:response['files'][name]=file_entry(encode(device.logs[name]))
 _,current=ct.bt.source_and_current(profile)
 return req,device,result,response,current
def review_fixture(profile,**kwargs):
 req,device,result,response,current=model(profile,**kwargs);value,raws=p.validate_records(req,encode(req),response,w)
 paths=p.remote_paths(req['transaction_id'])
 names={'result':'result.json','worker_process':'process-private.json','before':'before-private.json','stopped':'stopped-private.json',
  'after':'after-private.json','supervisor_launch':'launch-receipt-private.json','worker_launch':'worker-launch-receipt-private.json',
  'worker_terminal':'worker-terminal-private.json','supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json'}
 originals={key:raws[name] for key,name in names.items()}
 originals.update(request=encode(req),worker_source=ct.worker_raw,supervisor_source=ct.sup_raw)
 rollback=dict(transaction_id=req['transaction_id'],request_sha256=p.sha(encode(req)),result_sha256=p.sha(raws['result.json']),host_binding_sha256='a'*64,
  worker_sha256=p.WORKER,supervisor_sha256=p.SUPERVISOR,evidence={key:dict(path=paths[key],sha256=p.sha(raw)) for key,raw in originals.items()})
 review=dict(request=req,identity=req['identity'],current=current,rollback=rollback,post_restore_probe={key:'b'*64 for key in ['stdin_sha256','stdout_sha256','child_sha256','terminal_sha256']})
 guard=p.make_guard('irq-native-usb-pm-rollback-activate-device-fixture','c'*48,review)
 return req,device,result,response,current,guard,originals

class DeviceDelta(unittest.TestCase):
 def test_fifteen_original_helpers_and_exact_hardware_prefix_tails(self):
  sources.source_check();old=HERE.parent/'usb-irq-protection-rollback-restart-candidate'
  def funcs(path):
   text=path.read_text();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
  before,after=funcs(old/'common.py'),funcs(HERE/'common.py')
  reuse=json.loads((HERE/'source-reuse.json').read_bytes())
  self.assertEqual(len(reuse['unchanged_common_functions']),15)
  for name in reuse['unchanged_common_functions']:self.assertEqual(before[name],after[name])
  for name in ['eud-quiesce.py','eud-restart.py']:
   original=(old/name).read_bytes();expected=original.replace((old/'common.py').read_bytes(),(HERE/'common.py').read_bytes())
   self.assertEqual((HERE/name).read_bytes(),expected)
  self.assertIn('_ROLLBACK_MODULE.safe_stopped(data,now)',after['staged_health'])
  self.assertIn('_ROLLBACK_MODULE.retained(_RESTORED_AFTER,data)',after['staged_health'])

 def test_three_profiles_real_records_exact_current_notes_cache_and_target(self):
  for profile in w.PROFILES:
   req,device,result,response,current,guard,originals=review_fixture(profile)
   path=c.ROOT/guard['transaction_id']/'guard-private.json';c.validate_meta_shape(guard,path)
   self.assertEqual(guard['partitions'],['logdump']);self.assertEqual(guard['unchanged_boot_sha256'],w.BOOT)
   self.assertEqual(guard['rollback_logdump_sha256'],w.LOGDUMP502);self.assertFalse(guard['runtime_validation_accepted'])
   bad=copy.deepcopy(response);raw=p.decoded_files(bad)['after-private.json'];after=json.loads(raw);after['current_cache']['instance_inode']+=1
   bad['files']['after-private.json']=file_entry(encode(after))
   with self.assertRaises(ValueError):p.validate_records(req,encode(req),bad,w)
   for field,value in [('partitions',['boot']),('unchanged_boot_sha256','0'*64),('rollback_logdump_sha256',w.LOGDUMP504)]:
    wrong=copy.deepcopy(guard);wrong[field]=value
    with self.assertRaises(ValueError):c.validate_meta_shape(wrong,path)

 def test_distinct_post_restore_probe_request_cache_and_time(self):
  for profile in w.PROFILES:
   req,device,result,response,current=model(profile)
   expected=p.post_probe_request(req,p.sha(encode(result)),'a'*64)
   self.assertEqual(set(expected),{'schema','new_endpoint','profile','saved_source_binding_sha256'})
   self.assertNotEqual(expected,p.post_probe_request(req,'0'*64,'a'*64))
   report=dict(schema=expected['schema'],request=expected,identity_before=req['identity'],identity_after=req['identity'],current=current,
    cache_before=current['current_cache'],cache_after=current['current_cache'],started_boottime_ns=100_000_000_000,ended_boottime_ns=100_000_000_001)
   after=device.logs['after-private.json'];self.assertEqual(p.validate_probe(report,expected,req,after,w),current)
   for change in [lambda v:v.update(started_boottime_ns=1),lambda v:v['cache_after'].update(instance_inode=999),
    lambda v:v['current']['logdump'].update(sha256='0'*64)]:
    bad=json.loads(json.dumps(report));change(bad)
    with self.assertRaises((ValueError,RuntimeError)):p.validate_probe(bad,expected,req,after,w)

 def test_device_replays_actual_fourteen_records_and_original_source_verifier_only(self):
  for profile in w.PROFILES:
   req,device,result,response,current,guard,originals=review_fixture(profile)
   rawmap={p.remote_paths(req['transaction_id'])[key]:value for key,value in originals.items()};calls=[]
   module=dict(vars(w));module['Device']=SimpleNamespace(source_proof=lambda reader,request:calls.append(request['transaction_id']))
   proof_path=c.ROOT/guard['transaction_id']/'proof.py'
   def runpath(path):return vars(p) if Path(path)==proof_path else module
   with patch.object(c,'secure_file',side_effect=lambda path:Path(path)),patch.object(c,'file_sha',return_value=c.PROOF_SHA),
    patch.object(c,'raw_owned',side_effect=lambda path,**kwargs:rawmap[str(path)]),patch.object(c,'owned_directory',side_effect=lambda path:Path(path)),
    patch.object(c,'process_observation',side_effect=lambda receipt:dict(state='absent',pid=receipt['pid'])),patch.object(c.runpy,'run_path',side_effect=runpath):
    actual,_=c.rollback_material(guard)
   self.assertEqual(actual,req);self.assertEqual(calls,[req['transaction_id']]);self.assertEqual(c._CACHE_EXPECTED,req['current_cache'])
   self.assertEqual(c._RESTORED_AFTER,device.logs['after-private.json'])

 def test_stopped_recovery_preserves_full_faults_and_unknown_budget(self):
  for full,fault in [(True,False),(False,True)]:
   req,device,result,response,current=model(w.PROFILES[1],full=full,fault=fault)
   after=copy.deepcopy(device.logs['after-private.json']);after['openrc_started']=False
   with patch.object(c,'_ROLLBACK_MODULE',w),patch.object(c,'_RESTORED_AFTER',copy.deepcopy(after)),patch.object(c,'OLD_NOTES',w.NEW_NOTES):
    for budget in ['0',{'errno':61},None]:
     after['source']['current_max']=budget;accepted=c.staged_health(after,100.)
     self.assertTrue(accepted['no_source_budget_increase']);self.assertFalse(accepted['runtime_validation_accepted'])
    for change in [lambda v:v['state']['registers'].update({'08':0}),lambda v:v['limits'].update(input_ua=1000000),
     lambda v:v['sample'].update(cell1_uv=0),lambda v:v['current_cache'].update(instance_inode=999)]:
     bad=copy.deepcopy(after);change(bad)
     with self.assertRaises((ValueError,RuntimeError)):c.staged_health(bad,100.)
    if full:
     bad=copy.deepcopy(after);bad['sample'].update(logical_full=0,full_cause=0)
     with self.assertRaises(RuntimeError):c.staged_health(bad,100.)
    else:
     bad=copy.deepcopy(after);bad['sample']['latched']=0
     with self.assertRaises(RuntimeError):c.staged_health(bad,100.)

 def test_cache_held_real_readonly_fd_no_capture_and_changed_inode_refused(self):
  with tempfile.TemporaryDirectory() as top:
   instance=Path(top)/'instance';instance.mkdir();(instance/'driver').symlink_to('/sys/bus/platform/drivers/samurai-gauge-protection')
   original_path=Path
   def mapped(value,*args):return instance if str(value)=='/sys/devices/platform/samurai-gauge-protection' else original_path(value,*args)
   with patch.object(c,'Path',side_effect=mapped):
    for attempted,terminal in [(0,0),(1,1),(1,0)]:
     if c._MAC_FD is not None:os.close(c._MAC_FD);c._MAC_FD=None
     raw=f'schema=1 attempted={attempted} terminal={terminal}\n'.encode();attribute=instance/'mac_evidence';attribute.write_bytes(raw);info=attribute.stat()
     expected=dict(sha256=p.sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=info.st_dev,attribute_inode=info.st_ino,instance_inode=instance.stat().st_ino)
     try:
      if terminal==attempted:self.assertEqual(c.verify_current_cache(expected),expected)
      else:
       with self.assertRaises(ValueError):c.verify_current_cache(expected)
      self.assertEqual(attribute.read_bytes(),raw)
      replacement=instance/'replacement';replacement.write_bytes(raw);replacement.replace(attribute)
      with self.assertRaises(ValueError):c.verify_current_cache(expected)
     finally:
      if c._MAC_FD is not None:os.close(c._MAC_FD);c._MAC_FD=None

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(DeviceDelta);result=unittest.TextTestRunner(verbosity=2).run(suite)
 report=dict(passed=result.wasSuccessful(),groups=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  device_and_source_io_modeled=True,real_temp_readonly_cache_fd_used=True,actual_current_worker_safety_and_profile_used=True,
  actual_runtime_request_created=False,device_accessed=False,old_matrices_rerun=False,
  files={name:p.sha((HERE/name).read_bytes()) for name in ['test-device.py','proof.py','common.py','device-guard.inc','eud-quiesce.py','eud-restart.py','source-pins.json']})
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
