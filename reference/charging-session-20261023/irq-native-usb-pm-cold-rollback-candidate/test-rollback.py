"""Current two-file rollback integration; only IO/device/process boundaries modeled."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,tarfile,tempfile,unittest
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(HERE/'restore-worker.py','actual_current_cold_rollback')
package=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01')
payload=(package/'rollback-7cb-18e8-payload.tar.gz').read_bytes()
def contents(path):
 with tarfile.open(path) as tar:return {'/'+x.name:tar.extractfile(x).read() for x in tar.getmembers()}
forward=contents(package/'irq-native-pm-payload.tar.gz');original=contents(package/'rollback-7cb-18e8-payload.tar.gz')
oldtest=REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/test-stage.py'
text=oldtest.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='FakeFS')
def check(ok,message='condition'):
 if not ok:raise AssertionError(message)
scope=dict(Path=Path,os=os,m=m,old_bytes=forward,check=check)
exec(compile(ast.get_source_segment(text,node),str(oldtest),'exec'),scope);FakeFS=scope['FakeFS']
source=dict(boot_id='11111111-2222-4333-8444-555555555555',version=m.VERSION502,serial_sha256='1'*64,compatible_sha256='2'*64,rootfs_sha256='3'*64)
def cache(attempted=0):
 raw=f'schema=1 attempted={attempted} terminal={attempted}\n'.encode()
 return dict(sha256=m.sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=1,attribute_inode=101,instance_inode=102)
def request_for(profile):
 request=dict(schema='samurai-irq-native-usb-pm-cold-rollback-request-v1',transaction_id='irq-native-usb-pm-rollback-synthetic-0001',
  profile=profile,identity=copy.deepcopy(source),source_identity=copy.deepcopy(source),source_stage={},source_stage_observations={},
  activation=None,current_cache=cache(),payload_sha256=m.ROLLBACK_PAYLOAD,payload_base64=base64.b64encode(payload).decode(),
  worker_sha256=m.sha((HERE/'restore-worker.py').read_bytes()),lease_token='4'*48)
 if profile!=m.PROFILES[0]:
  request['identity'].update(boot_id='66666666-7777-4888-8999-000000000000',version=m.VERSION504 if profile==m.PROFILES[1] else m.VERSION502)
  request['activation']=dict(schema='samurai-irq-native-usb-pm-saved-activation-v1',activation_transaction_id='irq-native-usb-pm-activate-synthetic-0001',
   **{name:'5'*64 for name in ['context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256','reboot_request_sha256','reboot_result_sha256']},
   flash_claimed_ns=1,reboot_claimed_ns=2,boot_sha256=m.BOOT,logdump_sha256=m.expected_profile(request)['logdump'],
   action_pair=['flash-candidate','reboot-candidate'] if profile==m.PROFILES[1] else ['rollback-original','reboot-original'])
 return request

class FakeDevice(m.Device):
 def __init__(self,request,stopped=True,full=False):
  super().__init__();self.request=request;self.fs=FakeFS();self.logs={};self.stops=0;self.closed=False
  self.out=Path('/synthetic/device-rollback');self.fail_stop=False;self.expire=False;self.lose_full=False;self.change_cache=False
  profile=m.expected_profile(request)
  self.actual=dict(identity=copy.deepcopy(request['identity']),release=m.RELEASE,machine='aarch64',taint='0',
   boot=dict(bytes=100663296,sha256=m.BOOT),logdump=dict(bytes=67108864,sha256=profile['logdump']),
   notes=copy.deepcopy(profile['notes']),module_states={n:'live' for n in profile['notes']},current_cache=copy.deepcopy(request['current_cache']))
  sample=dict(valid=1,protection_ok=1,shadow=0,age_ms=5,cell1_uv=4300000,cell2_uv=4300000,pack_uv=8600000,temp_decic=265,
   error=0,stop_error=0,latched=0,fault=0,cycle_timeout=0,thermal_inhibit=0,gauge_charge_stop=0,online=1,
   logical_full=int(full),full_cause=3 if full else 0,session_seconds=0,desired_enable=0 if stopped or full else 1,
   full_holding=int(full and not stopped),hold_requested=int(full and not stopped))
  registers={'00':10,'01':0,'02':5,'03':0,'04':0x68,'05':0,'07':0,'08':8 if stopped else 0 if full else 0x10,'09':0,'0f':10,'13':2}
  self.observation=dict(read_start=99.5,read_end=99.8,sample=sample,notes=copy.deepcopy(profile['notes']),
   state=dict(boot_id=request['identity']['boot_id'],registers=registers,driver='samurai-mp2650',taint='0',
    camera_pm={str(x):'suspended' for x in range(4)},m2m=json.dumps(dict(users=0,running=False,fatal=False,pinned=False,orphans=0,first_error=0))),
   limits=dict(input_ua=500000,charge_ua=250000,cv_pack_uv=8725000),source=dict(current_max='500000'),
   charge_behaviour='inhibit-charge' if stopped else 'auto',protection_health='Good',
   protection=dict(id=0x2719,error=0,safety=0,pf=0,operation=0x300,manufacturing=0x18),current_cache=copy.deepcopy(request['current_cache']))
 def begin(self,request):pass
 def source_proof(self,request):return dict(source_stage_terminal_verified=True,model_boundary=True)
 def current(self,request,carriers=True):return copy.deepcopy(self.actual)
 def manager(self):return {}
 def verify_retained(self,manager):check(self.fs.files[m.MANIFEST]==forward[m.MANIFEST])
 def read_owned(self,path):return self.fs.reader(path)
 def now(self):return 100
 def observe(self,manager):return copy.deepcopy(self.observation)
 def backup(self,files,before):self.log('before-private.json',before)
 def stop(self,manager,meta):
  self.stops+=1
  if self.fail_stop:raise RuntimeError('modeled stop failure')
  self.observation['state']['registers']['08']=8;self.observation['charge_behaviour']='inhibit-charge'
  self.observation['sample'].update(desired_enable=0,full_holding=0,hold_requested=0)
  if self.lose_full:self.observation['sample'].update(logical_full=0,full_cause=0)
  if self.change_cache:self.observation['current_cache']['instance_inode']+=1
 def replace(self,path,raw):return m.atomic_replace(path,raw,self.request['transaction_id'],m.NEW_FILES[path],self.event,ops=self.fs,reader=self.read_owned)
 def check_window(self,request):
  if self.expire and self.fs.renames:raise RuntimeError('modeled lease expiry after first file')
 def verify_restored(self,files,manager):check(all(self.fs.files[p]==raw for p,raw in files.items()))
 def event(self,value):self.events.append(value)
 def log(self,name,value):self.logs[name]=copy.deepcopy(value)
 def finish(self,result):
  with patch.object(m,'read_owned',self.read_owned):super().finish(result)
 def close(self):self.closed=True
 def publish(self,result):self.logs['result.json']=copy.deepcopy(result)

class CurrentRollback(unittest.TestCase):
 def test_three_profiles_restore_only_two_exact_original_files(self):
  for profile in m.PROFILES:
   request=request_for(profile);device=FakeDevice(request);result=m.restore(request,device,True)
   self.assertTrue(result['restored'],result);self.assertEqual(result['status'],'staged_original/runtime_pending')
   self.assertEqual(device.fs.renames,m.ORDER);self.assertEqual(device.stops,0);self.assertTrue(device.closed)
   self.assertEqual(device.fs.files[m.USB],original[m.USB]);self.assertEqual(device.fs.files[m.MANIFEST],original[m.MANIFEST])
   self.assertFalse(result['module_or_carrier_action']);self.assertFalse(result['original_full_runtime_accepted'])
   self.assertEqual(device.actual['notes'],m.expected_profile(request)['notes'])

 def test_actual_seventeen_source_records_and_source_boot_ended_semantics(self):
  d=load(REF/'charging-session-20261023/irq-native-usb-pm-activation-device-candidate/test-delta.py','source_stage_fixture_definitions_only')
  with tempfile.TemporaryDirectory() as top:
   _,_,meta,records,captured,claim,raw,_=d.actual_stage_fixture(top)
   paths=m.source_paths(d.TX);raws={}
   for name,path in paths.items():
    if name=='worker_source':raws[name]=(REF/'charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate/stage-worker.py').read_bytes()
    elif name=='supervisor_source':raws[name]=(REF/'charging-session-20261023/irq-native-usb-pm-stage-host-candidate/supervisor.py').read_bytes()
    else:raws[name]=raw[Path(path).name]
   for profile in m.PROFILES:
    request=request_for(profile);request['source_identity']=copy.deepcopy(d.request['identity'])
    request['source_stage']=meta['stage'];request['source_stage_observations']=captured
    if profile==m.PROFILES[0]:request['identity']=copy.deepcopy(request['source_identity']);observed=captured
    else:
     observed={role:dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id']) for role in captured}
    result=m.verify_source_records(request,raws,observed,claim)
    self.assertTrue(result['source_stage_terminal_verified']);self.assertEqual(result['source_boot_ended'],profile!=m.PROFILES[0])
    if profile!=m.PROFILES[0]:
     with self.assertRaises(RuntimeError):m.verify_source_records(request,raws,captured,claim)
   request['source_stage_observations']=copy.deepcopy(captured);request['source_stage_observations']['worker']['state']='alive'
   with self.assertRaises(ValueError):m.verify_source_records(request,raws,observed,claim)

 def test_unknown_budget_latches_and_online_full_are_preserved(self):
  request=request_for(m.PROFILES[1])
  for budget in ['0',{'errno':61},None]:
   device=FakeDevice(request);device.observation['source']['current_max']=budget
   device.observation['sample'].update(latched=1,cycle_timeout=1,error=-110)
   result=m.restore(request,device,True);self.assertTrue(result['restored'],result)
   self.assertEqual(result['existing_fault_history']['latched'],1);self.assertEqual(result['existing_fault_history']['cycle_timeout'],1)
  device=FakeDevice(request,stopped=False,full=True);result=m.restore(request,device,True)
  self.assertTrue(result['restored'],result);self.assertEqual(device.stops,1)
  sample=device.logs['after-private.json']['sample'];self.assertEqual((sample['logical_full'],sample['full_cause'],sample['session_seconds']),(1,3,0))
  self.assertEqual(sample['full_holding'],0)

 def test_wrong_profile_cache_or_lost_full_rejected_before_disk_write(self):
  request=request_for(m.PROFILES[1])
  for change in [lambda d:d.actual['logdump'].update(sha256=m.LOGDUMP502),lambda d:d.actual['notes'].update(m.OLD_NOTES),
   lambda d:d.actual['current_cache'].update(instance_inode=777),lambda d:d.observation['protection'].update(error=-5),
   lambda d:d.observation['sample'].update(valid=0)]:
   device=FakeDevice(request);change(device);result=m.restore(request,device,True)
   self.assertFalse(result['restored']);self.assertEqual(device.fs.renames,[]);self.assertEqual(device.stops,0)
  for attr in ['lose_full','change_cache','fail_stop']:
   device=FakeDevice(request,stopped=False,full=True);setattr(device,attr,True);result=m.restore(request,device,True)
   self.assertFalse(result['restored']);self.assertEqual(device.fs.renames,[])
  bad=copy.deepcopy(request);raw=b'schema=1 attempted=1 terminal=0\n';bad['current_cache'].update(raw_base64=base64.b64encode(raw).decode(),sha256=m.sha(raw))
  with self.assertRaises(RuntimeError):m.unpack(bad)

 def test_atomic_failure_and_lease_expiry_leave_original_partial_state(self):
  request=request_for(m.PROFILES[1]);device=FakeDevice(request);device.expire=True
  result=m.restore(request,device,True);self.assertFalse(result['restored']);self.assertEqual(device.fs.renames,[m.USB]);self.assertEqual(result['disk_state'],'partial_known')
  for phase in ['rename','directory-fsync','readback']:
   device=FakeDevice(request);device.fs.failure=(m.MANIFEST,phase);result=m.restore(request,device,True)
   self.assertFalse(result['restored']);self.assertEqual(result['primary_error']['atomic_stage'],phase)
   self.assertTrue(device.closed);self.assertEqual(device.stops,0);self.assertFalse(result['automatic_replay_or_rollback'])

 def test_current_untouched_cache_fd_rebind_and_cleanup_errors(self):
  request=request_for(m.PROFILES[1]);expected=request['current_cache'];raw=base64.b64decode(expected['raw_base64']);inode=[101]
  attribute=SimpleNamespace(stat=lambda:SimpleNamespace(st_dev=1,st_ino=inode[0]))
  driver=SimpleNamespace(resolve=lambda:SimpleNamespace(as_posix=lambda:'/sys/bus/platform/drivers/samurai-gauge-protection'))
  class Node:
   def __truediv__(self,name):return attribute if name=='mac_evidence' else driver
   def stat(self):return SimpleNamespace(st_ino=102)
  fakeos=SimpleNamespace(fstat=lambda fd:SimpleNamespace(st_dev=1,st_ino=101),lseek=lambda *args:0,read=lambda *args:raw,SEEK_SET=os.SEEK_SET)
  device=m.Device();device.request=request;device.mac_fd=55
  with patch.object(m,'Path',return_value=Node()),patch.object(m,'os',fakeos):
   self.assertEqual(device.cache_evidence(),expected);inode[0]=999
   with self.assertRaises(RuntimeError):device.cache_evidence()
  events=[]
  def close(fd):
   events.append(fd)
   if fd==55:raise OSError('modeled MAC close error')
  device.journal=SimpleNamespace(close=lambda:events.append('journal'));device.lock=56
  with patch.object(m.os,'close',side_effect=close):
   with self.assertRaises(RuntimeError):device.close()
  self.assertEqual(events,[55,'journal',56]);self.assertIsNone(device.mac_fd);self.assertIsNone(device.lock)

 def test_original_atomic_safety_and_base_methods_are_reused(self):
  old=REF/'charging-oem-audit-20261023/usb-irq-protection-rollback-candidate/restore-worker.py'
  def defs(path):
   text=path.read_text();tree=ast.parse(text);return text,tree,{n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  source,tree,olddefs=defs(old);new,ntree,newdefs=defs(HERE/'restore-worker.py');reuse=json.loads((HERE/'source-reuse.json').read_bytes())
  self.assertEqual(len(reuse['exact_functions']),12)
  self.assertTrue(all(olddefs[n]==newdefs[n] for n in reuse['exact_functions']))
  prior=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Device');current=next(n for n in ntree.body if isinstance(n,ast.ClassDef) and n.name=='BaseDevice')
  a={n.name:ast.get_source_segment(source,n) for n in prior.body if isinstance(n,ast.FunctionDef)}
  b={n.name:ast.get_source_segment(new,n) for n in current.body if isinstance(n,ast.FunctionDef)}
  self.assertEqual(len(reuse['exact_base_device_methods']),20);self.assertTrue(all(a[n]==b[n] for n in reuse['exact_base_device_methods']))
  self.assertEqual(m.STAGE_RULES,(REF/'charging-session-20261023/irq-native-usb-pm-activation-device-candidate/common.py').read_text())

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CurrentRollback))
 report=dict(passed=result.wasSuccessful(),methods=result.testsRun,failures=len(result.failures),errors=len(result.errors),
  real_fixed_two_file_payloads_used=True,actual_atomic_function_with_fake_filesystem_used=True,
  actual_source_stage_algorithm_with_device_and_process_models_used=True,
  fresh_device_identity_cache_and_activation_actions_modeled=True,actual_runtime_request_created=False,
  device_accessed=False,old_matrices_rerun=False,
  tested_files={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['restore-worker.py','current-body.py.inc','prepare.py','test-rollback.py']})
 (HERE/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
