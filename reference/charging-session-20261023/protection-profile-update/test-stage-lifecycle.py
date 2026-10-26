"""Actual stage loop and filesystem; fake only phone identity/hardware/library I/O."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,stat,tempfile,time,types
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('profile_lifecycle_adapter',HERE/'host.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a);u=a.u
source=(u.OUT/'stage-worker.py').read_bytes();request=u.request();base=u.BASE/'protection-observed-2719-cohort-private-02'
evidence=u.BASE/'protection-profile-update-live-20261024-02/raw-29ae4096/device-stage'
real_before=json.loads((evidence/'before-private.json').read_bytes());real_stopped=json.loads((evidence/'stopped-private.json').read_bytes())
sha=lambda raw:hashlib.sha256(raw).hexdigest()
cases=[]
for failure in [None,'verify-new','rename-third']:
 w=u.load(u.OUT/'stage-worker.py','profile_stage_'+str(failure))
 # Exercise the real frozen request/archive before remapping paths to temp.
 w.unpack(request)
 with tempfile.TemporaryDirectory(prefix='profile-stage-cycle-') as name:
  root=Path(name);targets=[root/'protection.ko',root/'samurai-charging',root/'manifest.json'];modes=[0o600,0o755,0o600]
  oldmeta=json.loads((base/'manifest-old.json').read_bytes());newmeta=copy.deepcopy(oldmeta)
  old_protection=oldmeta['modules']['samurai-gauge-protection']['target'];old_service='/usr/sbin/samurai-charging'
  oldmeta['modules']['samurai-gauge-protection']['target']=str(targets[0])
  for original,target in [(old_protection,targets[0]),(old_service,targets[1])]:oldmeta['installed_files'][str(target)]=oldmeta['installed_files'].pop(original)
  newmeta=copy.deepcopy(oldmeta);newmeta['adapter_revision']='protection-observed-2719-profile-01'
  module_old=(u.BASE/'protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko').read_bytes()
  module_new=(u.BASE/'protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko').read_bytes()
  service_old=(base/'service-old.py').read_bytes();service_new=(base/'service-new.py').read_bytes()
  newmeta['modules']['samurai-gauge-protection']['sha256']=sha(module_new);newmeta['installed_files'][str(targets[0])]=sha(module_new);newmeta['installed_files'][str(targets[1])]=sha(service_new)
  old=[module_old,service_old,(json.dumps(oldmeta,indent=2)+'\n').encode()];new=[module_new,service_new,(json.dumps(newmeta,indent=2)+'\n').encode()]
  w.USB,w.SERVICE,w.MANIFEST=map(str,targets);w.ORDER=list(map(str,targets));w.MODES={str(p):mode for p,mode in zip(targets,modes)}
  w.OLD_FILES={str(p):sha(raw) for p,raw in zip(targets,old)};w.NEW_FILES={str(p):sha(raw) for p,raw in zip(targets,new)}
  w.OLD=sha(old[2]);w.NEW=sha(new[2]);w.unpack=lambda request:({str(p):raw for p,raw in zip(targets,new)},newmeta)
  w.manifest_delta(oldmeta,newmeta)
  for p,raw,mode in zip(targets,old,modes):p.write_bytes(raw);p.chmod(mode)
  class Device(w.Device):
   def __init__(self):
    super().__init__((json.dumps(request,indent=2)+'\n').encode());self.is_stopped=False;self.control_calls=[];self.loads=[];self.injected=False
   def identity(self,r):return real_before['identity']
   def begin(self,r):self.request=r;self.out=root/'evidence';self.out.mkdir(mode=0o700)
   def check_window(self,r):pass
   def module_state(self,name='samurai-mp2650'):return 'live'
   def mac_evidence(self):return real_before['mac_evidence']
   def notes_match(self,manager,old,backups=False):assert self.module_state()=='live'
   def manager(self,expected):
    actual=sha(targets[1].read_bytes());assert expected==actual;self.loads.append(actual)
    def verify():
     meta=json.loads(targets[2].read_bytes())
     for p in targets[:2]:assert sha(p.read_bytes())==meta['installed_files'][str(p)]
     return meta
    def command(meta,action):
     assert actual==w.SERVICE_SHA==sha(targets[1].read_bytes()) and action=='stop'
     self.control_calls.append((actual,action));self.is_stopped=True
    def registers():return copy.deepcopy((real_stopped if self.is_stopped else real_before)['registers'])
    return dict(_r8_code_sha256=actual,verify=verify,command=command,live=types.SimpleNamespace(registers=registers))
   def verify(self,manager):
    meta=w.SnapshotBase.verify(self,manager)
    if failure=='verify-new' and not self.injected and sha(targets[2].read_bytes())==w.NEW:
     self.injected=True;raise RuntimeError('injected complete new-manifest verification failure')
    return meta
   def observe(self,manager):
    value=copy.deepcopy(real_stopped if self.is_stopped else real_before);now=time.clock_gettime(time.CLOCK_BOOTTIME)
    value.update(read_start=now-0.005,read_end=now);return value
  actual_atomic=w.atomic_replace
  class FailedRename:
   def __getattr__(self,key):return getattr(os,key)
   def replace(self,src,dst):
    if Path(dst)==targets[2]:raise OSError(5,'injected third-file rename failure')
    return os.replace(src,dst)
  if failure=='rename-third':
   def atomic(*args,**kw):return actual_atomic(*args,**kw,ops=FailedRename())
   w.atomic_replace=atomic
  device=Device();result=w.stage(request,device,True)
  assert device.control_calls==[(w.SERVICE_SHA,'stop')],'new manager must never mutate charge control in this stage'
  if failure is None:
   assert result['staged'] and result['status']=='staged/runtime_pending' and result['disk_state']=='all_new_fsynced' and not result['primary_error'] and not result['recovery_error']
   expected=new
  else:
   assert not result['staged'] and result['restored_original_disk'] and result['status']=='failed_old_disk_restored_inhibited' and result['disk_state']=='all_old' and result['recovery_error'] is None
   expected=old
  assert all(p.read_bytes()==raw and stat.S_IMODE(p.stat().st_mode)==mode for p,raw,mode in zip(targets,expected,modes))
  assert os.access(targets[1],os.X_OK) and sha(service_new) in device.loads,'new service must be freshly loaded for read-only checks'
  cases.append(dict(failure=failure,passed=True,status=result['status'],service_executable=True,control_calls_old_stop_only=True))
assert (u.OUT/'stage-worker.py').read_bytes()==source
record=dict(passed=True,cases=cases,worker_sha256=sha(source),actual_stage_atomic_replace_Device_replace_and_readonly_verify_registers=True,
 request_archive_checked_before_fixture_remapping=True,identity_hardware_and_module_import_OS_boundaries_faked=True,phone_accessed=False)
u.save(HERE/'stage-lifecycle-result.json',record);print(json.dumps(record))
