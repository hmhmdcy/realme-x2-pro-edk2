"""Test the actual m2m worker teardown against explicit ownership states."""
from pathlib import Path
import copy,json,tempfile
import host
HERE=Path(__file__).resolve().parent;source=(HERE/'m2m-worker.py').read_text()
compile(source,str(HERE/'m2m-worker.py'),'exec');compile((HERE/'launch-m2m.py').read_text(),str(HERE/'launch-m2m.py'),'exec')
a=source.index('finally:\n try:')+len('finally:\n');b=source.index(' deadline=time.monotonic()+5',a)
body=''.join(line[1:]+'\n' for line in source[a:b].splitlines())
rows=[]
for case in ['clean','client-live','held-idle','cleanup-fails','unacknowledged-snapshot','other-user','core-retained']:
 root=Path(tempfile.mkdtemp(prefix='worker-'+case+'-',dir=host.PRIVATE));firmware=root/'firmware.bin';firmware.write_bytes(b'owned')
 modules={n:True for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem']}
 status=dict(users=0,running=False,pinned=False,orphans=0)
 if case in ['held-idle','cleanup-fails']:status.update(pinned=True,orphans=1)
 if case=='other-user':status['users']=1
 events=[];observation=dict(passed=True)
 if case=='unacknowledged-snapshot':observation['collector_result']=dict(captured=True,owned_snapshot_acknowledged=False)
 class Sys:
  def __init__(self,value):self.value=value
  def exists(self):
   assert self.value.startswith('/sys/module/')
   return modules.get(self.value.rsplit('/',1)[-1],False)
  def read_text(self):
   assert self.value.endswith('/parameters/sfr')
   return ''
  def glob(self,pattern):
   assert self.value=='/sys/class/devcoredump'
   return []
  def write_text(self,text):
   assert self.value.endswith('/cleanup') and text=='1' and observation.get('cleanup_attempted')
   events.append('cleanup')
   if case=='cleanup-fails':raise OSError('injected reset failure')
   status.update(pinned=False,orphans=0,running=False)
 def path(*args):
  value=str(Path(*args))
  return Sys(value) if value.startswith('/sys/') else Path(*args)
 def read_m2m():
  assert case!='client-live'
  return copy.deepcopy(status)
 def read_result():
  owned=case=='core-retained' or status['pinned']
  return dict(terminal=True,cpu_enabled=False,power_held=owned,backing_owned=owned,mapped_bytes=int(owned),remaining_groups=int(owned),remaining_domains=int(owned),ipe_dma_pending=False,request_fw_mapped=False)
 def releasable(r):return r['terminal'] and not any(r[k] for k in ['cpu_enabled','power_held','backing_owned','mapped_bytes','remaining_groups','remaining_domains','ipe_dma_pending','request_fw_mapped'])
 def save(phase,**values):observation.update(phase=phase,**values)
 def run(args):
  assert args[0]=='rmmod'
  name=args[1]
  if name=='camss_icp_a5_boot_test':assert not any(status.values()) and case not in ['client-live','unacknowledged-snapshot','core-retained']
  if name=='camss_icp_a5_m2m':assert not modules['camss_icp_a5_boot_test']
  if name=='v4l2_mem2mem':assert not modules['camss_icp_a5_m2m']
  if name=='qcom_camss_icp_a5_core':assert not modules['camss_icp_a5_m2m'] and not modules['camss_icp_a5_boot_test']
  modules[name]=False;events.append(name)
 scope=dict(ROOT=root,Path=path,json=json,client=type('Client',(),{'poll':lambda self:None if case=='client-live' else 0})(),
  observation=observation,collector=None,collector_log=None,attempted_test=True,test='camss_icp_a5_boot_test',core='qcom_camss_icp_a5_core',
  cleanup_attempted=case=='clean',owned_adapter=True,owned_helper=True,owned_core=True,owned_firmware=True,firmware=firmware,
  save=save,run=run,read_m2m=read_m2m,read_result=read_result,releasable=releasable)
 exec(compile(body,'actual-worker-finally','exec'),scope)
 removed=not any(modules.values());expected=case in ['clean','held-idle']
 assert removed==expected,(case,events,observation)
 if case=='client-live':assert not events and observation['requires_cleanup_attention']
 if case=='cleanup-fails':assert events==['cleanup'] and 'injected reset failure' in observation['cleanup_error']
 assert firmware.exists()!=removed
 rows.append(dict(case=case,removed=removed,passed=True))
report=dict(stage=386,actual_m2m_worker_teardown_statements=True,tests=rows,active_client_never_removed_or_queried_through_blocking_status=True,
 failed_cleanup_never_retried_or_freed_blindly=True,unacknowledged_snapshot_and_unknown_core_ownership_preserved=True,
 only_owned_modules_removed_in_dependency_order=True,no_hardware_operations=True,passed=True)
(HERE/'worker-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
