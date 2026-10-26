from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('actual_recharge_protocol',HERE/'recharge-exercise-r2.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class IO:
    def __init__(self,failure=None):self.clock=0;self.behaviour='auto';self.actions=[];self.resume_at=None;self.failure=failure
    def now(self):return self.clock
    def sleep(self,n):self.clock+=n
    def cancelled(self):return self.failure=='cancel' and self.clock>=10
    def save(self,name,value):pass
    def command(self,action):
        self.actions.append(action);self.behaviour='inhibit-charge' if action=='stop' else 'auto'
        if action=='resume':self.resume_at=self.clock
    def observe(self):
        ready=self.failure not in ['timeout','cancel','unsafe'] and self.clock>=20
        full=not (self.failure!='rebound' and self.resume_at is not None and ready and self.clock-self.resume_at>=30)
        return dict(boottime=self.clock,behaviour=self.behaviour,register08=8 if self.behaviour=='inhibit-charge' else 16,
            sample=dict(logical_full=int(full),full_holding=int(full),full_cause=3 if full else 0,desired_enable=int(not full and self.behaviour=='auto'),
                        session_seconds=int(self.clock-self.resume_at-30) if not full else 0,cell1_uv=4190000 if ready else 4320000,cell2_uv=4189000 if ready else 4319000,gauge_current_ua=-50000))
    def validate(self,value):
        if self.failure=='unsafe' and self.behaviour=='inhibit-charge' and self.clock>=10:raise RuntimeError('modeled persistent protection fault')
def timer(io,seconds):
    assert seconds==60 and io.behaviour=='auto';return dict(passed=True,hardware_modeled=True)
cases=[]
for failure in [None,'timeout','cancel','unsafe','rebound']:
    io=IO(failure);r=p.observe_recharge(io,timer,30);assert r['passed']==(failure is None)
    assert io.actions==(['stop'] if failure=='unsafe' else ['stop','resume'])
    if failure=='timeout':assert r['stop_reason']=='bounded_timeout'
    if failure=='cancel':assert r['stop_reason']=='cancelled'
    if failure=='rebound':assert r['threshold_reached'] and r['resume_confirmed'] and not r.get('recharge_observed') and not r['timer']
    cases.append(dict(failure=failure,passed=True,actions=io.actions,experiment_passed=r['passed']))
record=dict(passed=True,cases=cases,actual_recharge_protocol_body=True,hardware_clock_samples_and_nested_timer_modeled=True,phone_accessed=False)
with (HERE/'recharge-r2-test-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False)))
