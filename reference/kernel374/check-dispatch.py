from pathlib import Path
import copy,json
import host
HERE=Path(__file__).resolve().parent;s=(HERE/'boot-worker.py').read_text();a=s.index(' ready_result=read_result()');b=s.index(' deadline=time.monotonic()+20',a)
body='def dispatch():\n'+s[a:b]
ready=dict(terminal=True,phase='ready',error=0,cpu_release_attempted=False,irq_enabled=False,backing_owned=False,cpu_enabled=False,power_held=False,mapped_bytes=0,remaining_groups=0,remaining_domains=0)
rows=[]
for case in range(9):
 state=copy.deepcopy(ready);events=[]
 if case==2:state['phase']='done'
 if case==3:state['backing_owned']=True
 if case==4:state['cpu_release_attempted']=True
 if case==5:state['terminal']=False
 if case==7:state['irq_enabled']=True
 if case==8:state['error']=-5
 class File:
  def __init__(self,p):self.p=p
  def read_text(self):assert self.p=='/sys/module/test/parameters/bound_seen';return 'N' if case==1 else 'Y'
  def write_text(self,text):assert self.p=='/sys/bus/platform/devices/ac10000.samurai-icp356-boot/run' and text=='1' and events==['binding-ready','explicit-post-bind-run'];events.append('run-write');return 1
 def save(phase,**values):events.append(phase)
 def releasable(r):return r.get('terminal') and not any(r.get(k) for k in ['backing_owned','cpu_enabled','power_held','mapped_bytes','remaining_groups','remaining_domains'])
 scope=dict(Path=lambda *parts:File('/'.join(parts)),test='test',read_result=lambda:state,releasable=releasable,save=save,collector=type('Collector',(),{'poll':lambda self:0 if case==6 else None})())
 exec(compile(body,'actual-worker-dispatch','exec'),scope);failed=False
 try:scope['dispatch']()
 except AssertionError:failed=True
 assert failed==(case!=0) and events.count('run-write')==(case==0),(case,events)
 rows.append(dict(case=case,run_writes=events.count('run-write'),passed=True))
report=dict(stage=374,actual_worker_dispatch_guard_and_write=True,tests=rows,sysfs_and_collector_providers_mocked=True,
 ready_bound_and_live_collector_required_before_run=True,binding_state_saved_before_kernel_run=True,
 no_hardware_or_actual_binding_claim=True,phone_operations=False,passed=True)
(HERE/'dispatch-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
