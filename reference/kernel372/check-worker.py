"""Exercise actual worker decision/cleanup statements with injected sysfs providers."""
from pathlib import Path
import copy,json,tempfile,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;source=(HERE/'boot-worker.py').read_text()
a=source.index(' held=bool(');b=source.index('\nexcept BaseException as error:',a);middle=source[a:b]
a=source.index("   if result.get('phase')=='failed-held' and not cleanup_attempted:");b=source.index("   (ROOT/'sfr-private.txt')",a);fallback=source[a:b]
body='def exercise(result):\n cleanup_attempted=False\n try:\n'+''.join(' '+line+'\n' for line in middle.splitlines())+' except BaseException as error:\n  observation["fixture_error"]=str(error)\n finally:\n'+''.join(line[1:]+'\n' for line in fallback.splitlines())+' return cleanup_attempted\n'
held=dict(terminal=True,phase='failed-held',error=-121,cleanup_error=0,pc_error=0,cpu_release_attempted=True,cpu_enabled=False,irq_enabled=False,reset_asserted=True,power_held=True,backing_owned=True,mapped_bytes=6414336,remaining_groups=7,remaining_domains=7,init_response=3,init_done=False,ping_done=False,pc_done=False,fw_version=16777472,interrupts=0,messages=0,watchdogs=0,protocol_errors=0)
good=dict(captured=True,owned_snapshot_acknowledged=True,snapshot_saved=True,snapshot=dict(code_page_match=True))
rows=[]
for case in ['held','code-mismatch','ack-failed','cleanup-failed','unknown-ownership','ready','pre-cpu-failed']:
 root=Path(tempfile.mkdtemp(prefix='worker-'+case+'-',dir=P));initial=copy.deepcopy(held);collected=copy.deepcopy(good)
 if case=='code-mismatch':collected.update(snapshot_saved=False,snapshot=dict(code_page_match=False))
 if case=='ack-failed':collected['owned_snapshot_acknowledged']=False
 if case=='unknown-ownership':initial['phase']='start';initial['cpu_enabled']=True
 if case in ['ready','pre-cpu-failed']:
  initial.update(phase='done',power_held=False,backing_owned=False,mapped_bytes=0,remaining_groups=0,remaining_domains=0,cpu_release_attempted=case=='ready')
  collected=dict(captured=False,snapshot_saved=False)
  if case=='ready':initial.update(error=0,init_response=1,init_done=True,ping_done=True,pc_done=True,interrupts=3,messages=3)
 (root/'collector-result.json').write_text(json.dumps(collected));events=[];observation={};live_state=copy.deepcopy(initial)
 class Cleanup:
  def write_text(self,text):
   assert text=='1' and observation.get('cleanup_attempted'),events
   events.append('cleanup-write')
   if case=='cleanup-failed':raise OSError('injected cleanup failure')
   live_state.update(phase='cleaned',power_held=False,backing_owned=False,mapped_bytes=0,remaining_groups=0,remaining_domains=0)
 def path(value):
  assert value=='/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup';return Cleanup()
 def save(phase,**values):events.append(phase);observation.update(phase=phase,**values)
 def releasable(r):return r.get('terminal') and not any(r.get(k) for k in ['backing_owned','cpu_enabled','power_held','mapped_bytes','remaining_groups','remaining_domains'])
 scope=dict(ROOT=root,Path=path,json=json,time=time,collector=type('Collector',(),{'poll':lambda self:None})(),observation=observation,save=save,read_result=lambda:copy.deepcopy(live_state),releasable=releasable)
 exec(compile(body,'actual-worker-block','exec'),scope)
 thrown=False
 try:scope['exercise'](copy.deepcopy(initial))
 except OSError:thrown=True
 expected=case not in ['unknown-ownership','ready','pre-cpu-failed']
 assert events.count('cleanup-write')==int(expected),(case,events)
 assert not thrown
 if case=='cleanup-failed':assert 'injected cleanup failure' in observation['fixture_error'] and observation['cleanup_attempted']
 if case=='held':assert observation['diagnostic_completed'] and not observation['firmware_handshake_passed']
 if case=='code-mismatch':assert not observation['diagnostic_completed']
 if case=='ready':assert observation['firmware_handshake_passed']
 if case in ['ready','pre-cpu-failed']:assert (root/'collector-stop').exists()
 rows.append(dict(case=case,cleanup_writes=events.count('cleanup-write'),passed=True))
report=dict(stage=372,actual_worker_held_snapshot_cleanup_and_error_fallback_blocks=True,sysfs_and_module_providers_mocked=True,
 tests=rows,cleanup_attempt_saved_before_write=True,no_cleanup_retry_after_started_attempt=True,
 incomplete_ownership_never_assumed_released=True,handshake_not_claimed_for_collected_fault=True,phone_operations=False,passed=True)
(HERE/'worker-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
