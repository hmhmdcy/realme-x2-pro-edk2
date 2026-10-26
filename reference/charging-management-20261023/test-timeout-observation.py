"""Failure/acceptance controls for the timer observer. Mock time is NOT hardware evidence."""
from pathlib import Path
import importlib.util,json
spec=importlib.util.spec_from_file_location('actual_timer_observer',Path(__file__).with_name('timeout-observation.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class IO:
    def __init__(self,case):
        self.case=case;self.t=1000.;self.start=self.t;self.auto=False
        self.stops=0;self.balances=0;self.records=0
        self.attempts=0
    def now(self):return self.t
    def sleep(self,seconds):
        assert seconds>=0
        self.t+=seconds
        if self.case=='gap' and self.t-self.start>100:self.t+=31
        if self.case=='clock_rollback' and self.t-self.start>100:self.t-=20
    def observe(self):
        elapsed=self.t-self.start
        seconds=min(36000,200+int(elapsed))
        timeout=int(seconds==36000)
        if self.case=='initial_old':seconds+=1000
        if self.case=='early_timeout' and elapsed>=100:timeout=1;seconds=36000
        if self.case=='fast_counter' and elapsed>100:seconds+=15
        if self.case=='stalled_counter':seconds=200
        if self.case=='counter_reset' and elapsed>100:seconds=0
        if self.case=='already_expired':seconds=36000;timeout=1
        if self.case=='no_timeout':timeout=0
        if self.case=='AUTO_clears' and self.auto:seconds=0;timeout=0
        s=dict(cell1_uv=3800000,cell2_uv=3803000,temp_decic=300,
               logical_full=0,full_holding=0,full_cause=0,
               session_seconds=seconds,cycle_timeout=timeout,latched=timeout,
               error=-62 if timeout else 0,stop_error=0,desired_enable=0 if timeout else 1)
        if self.case=='Full' and elapsed>100:s.update(logical_full=1,full_cause=3)
        if self.case=='hot' and elapsed>100:s['temp_decic']=370
        if self.case=='low_voltage' and elapsed>100:s['cell1_uv']=3450000
        if self.case=='stop_failure' and timeout:s['stop_error']=-5
        reg=8 if timeout else 0x10
        if self.case=='not_stopped' and timeout:reg=0x10
        if self.case=='ordinary_fault' and elapsed>100:s['error']=-5
        return dict(boottime=self.t,behaviour='inhibit-charge' if self.case=='wrong_mode' else 'auto',
                    register08=reg,sample=s)
    def validate(self,value):
        if self.case=='IO_failure' and self.t-self.start>100:raise OSError('actual sample unavailable')
        if self.case=='validate_failure' and self.t-self.start>100:
            error=AssertionError('validation failed: source.online')
            error.stage='validate:timing'
            raise error
    def attempt(self,phase,value):self.attempts+=1
    def record(self,phase,value):self.records+=1
    def cancelled(self):
        return (self.case=='cancel' and self.t-self.start>100 or
                self.case=='cancel_at_timeout' and self.t-self.start>=35800 or
                self.case=='cancel_after_AUTO' and self.auto)
    def balance(self,value):self.balances+=1
    def stop_load(self):
        self.stops+=1
        if self.case=='cleanup_failure':raise RuntimeError('load join failed')
    def request_auto(self):
        if self.case=='AUTO_IO_failure':raise OSError('AUTO sysfs write failed')
        self.auto=True


cases=['success','initial_old','early_timeout','fast_counter','stalled_counter','counter_reset',
       'already_expired','AUTO_clears','Full','hot','low_voltage','stop_failure','not_stopped',
       'ordinary_fault','wrong_mode','IO_failure','cancel','gap','clock_rollback','cleanup_failure',
       'no_timeout','cancel_at_timeout','cancel_after_AUTO','AUTO_IO_failure','validate_failure']
results={}
for case in cases:
    io=IO(case);result=m.observe_timeout(io)
    assert result['passed']==(case=='success'),(case,result)
    assert io.stops>=1,(case,'cleanup was not attempted')
    if case=='success':
        assert result['observed_seconds']==35800 and result['initial_session_seconds']==200
        assert result['timeout_stop_verified'] and result['timeout_survived_auto'] and io.auto
    if case=='cancel':assert result['reason']=='cancelled' and not io.auto
    if case=='no_timeout':assert result['reason']=='deadline_without_timeout' and not io.auto
    if case=='cancel_at_timeout':assert result['reason']=='cancelled_after_timeout' and not io.auto
    if case=='cancel_after_AUTO':assert result['reason']=='cancelled_after_AUTO' and io.auto
    if case=='cleanup_failure':assert result['cleanup_error']
    if case in ('validate_failure','IO_failure'):
        assert result['error_type'] and result['error_stage'] and result['error_traceback'],(case,result)
        assert result['last_good'] is not None,(case,result)
    if case=='validate_failure':
        assert result['last_attempt']['phase']=='timing' and io.attempts>0
    results[case]=dict(passed=result['passed'],reason=result['reason'],error=result['error'],cleanup_error=result['cleanup_error'])
print(json.dumps({'control_tests_passed':True,'cases':len(cases),'hardware_tested':False,'results':results}))
