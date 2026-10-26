from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('actual_bounded_timer_protocol',HERE/'exercise.py');e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
class IO:
    def __init__(self,failure=None):self.clock=0;self.actions=[];self.behaviour='auto';self.failure=failure;self.resume_at=None
    def now(self):return self.clock
    def sleep(self,seconds):self.clock+=seconds
    def command(self,action):
        self.actions.append(action)
        if self.failure=='unknown-stop' and action=='stop':raise OSError('modeled unknown stop')
        self.behaviour='inhibit-charge' if action=='stop' else 'auto'
        if action=='resume':self.resume_at=self.clock
    def observe(self):
        if self.behaviour=='inhibit-charge':counter=100+(int(self.clock) if self.failure=='old-timer' else 0)
        else:counter=100+int(self.clock-(self.resume_at or 0))
        return dict(boottime=self.clock,behaviour=self.behaviour,register08=8 if self.behaviour=='inhibit-charge' else 16,
            sample=dict(desired_enable=int(self.behaviour=='auto'),logical_full=0,full_holding=0,session_seconds=counter))
    def validate(self,value):
        if self.failure=='unsafe-after-stop' and self.behaviour=='inhibit-charge':raise RuntimeError('modeled protection fault')
cases=[]
for failure in [None,'old-timer','unknown-stop','unsafe-after-stop']:
    io=IO(failure);result=e.exercise(io,20)
    assert result['passed']==(failure is None)
    if failure in [None,'old-timer']:assert io.actions==['stop','resume'] and io.behaviour=='auto'
    else:assert io.actions==['stop'] and not result['resume_attempted']
    cases.append(dict(failure=failure,passed=True,actions=io.actions,experiment_passed=result['passed']))
record=dict(passed=True,cases=cases,actual_protocol_body=True,OS_hardware_clock_and_policy_samples_modeled=True,phone_accessed=False)
with (HERE/'test-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False)))
