"""Check that live readiness refresh preserves the original idle requirements."""
from pathlib import Path
import copy,json
HERE=Path(__file__).resolve().parent;s=(HERE/'m2m-worker.py').read_text()
a=s.index(' ready_result=read_result();observation');b=s.index(" assert ready_result.get('terminal')",a)
body=''.join(line[1:]+'\n' for line in s[a:b].splitlines())
rows=[]
for case in ['stale-probe','already-idle','never-idle','unexpected-cpu','unexpected-job']:
 probe=dict(terminal=True,phase='ready',remaining_groups=3,remaining_domains=3,cpu_release_attempted=False)
 live=copy.deepcopy(probe)
 if case in ['already-idle','unexpected-cpu','unexpected-job']:probe.update(remaining_groups=0,remaining_domains=0)
 if case!='never-idle':live.update(remaining_groups=0,remaining_domains=0)
 if case=='unexpected-cpu':live['cpu_release_attempted']=True
 observation={};reads=0
 class Clock:
  now=0
  def monotonic(self):return self.now
  def sleep(self,n):self.now+=n
 clock=Clock()
 def read_result():
  global reads
  reads+=1
  return copy.deepcopy(probe if reads==1 else live)
 def read_m2m():return dict(jobs=int(case=='unexpected-job'))
 def releasable(r):return not r['remaining_groups'] and not r['remaining_domains'] and not r['cpu_release_attempted']
 def path(value):
  assert value.endswith('/power/runtime_status')
  return type('Attribute',(),{'read_text':lambda self:'active' if case=='never-idle' else 'suspended'})()
 def save(phase,**values):observation.update(phase=phase,**values)
 scope=dict(read_result=read_result,read_m2m=read_m2m,releasable=releasable,time=clock,Path=path,save=save,observation=observation)
 error=None
 try:exec(compile(body,'actual-post-bind-refresh','exec'),scope)
 except (AssertionError,RuntimeError) as e:error=type(e).__name__
 passed=error is None;assert passed==(case in ['stale-probe','already-idle'])
 if case=='stale-probe':assert observation['probe_snapshot_before_refresh']['remaining_groups']==3 and observation['ready_result']['remaining_groups']==0
 rows.append(dict(case=case,accepted=passed,passed=True))
report=dict(stage=386,actual_worker_readiness_refresh_loop=True,tests=rows,live_snapshot_required_before_original_idle_gate=True,
 no_firmware_or_power_control_operations=True,passed=True)
(HERE/'ready-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
