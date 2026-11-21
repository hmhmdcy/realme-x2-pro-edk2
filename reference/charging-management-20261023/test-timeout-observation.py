"""Failure/acceptance controls for the timer observer. Mock time is NOT hardware evidence."""
from pathlib import Path
import errno,importlib.util,json
spec=importlib.util.spec_from_file_location('actual_timer_observer',Path(__file__).with_name('timeout-observation.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


errno_names=('ENODATA','EAGAIN','ESTALE','ENOLINK','ETIMEDOUT')
errno_values={name:getattr(errno,name) for name in errno_names}


class IO:
    def __init__(self,case):
        self.case=case;self.t=1000.;self.start=self.t;self.auto=False
        self.stops=0;self.balances=0;self.records=0
        self.attempts=0;self.injected=False;self.gap_injected=False
        self.retry_calls=0;self.retry_exhausted_calls=0
        self.auto_request_attempts=0;self.auto_during_retry=[]
    def now(self):return self.t
    def sleep(self,seconds):
        assert seconds>=0
        self.t+=seconds
        if self.case=='one_gap' and not self.gap_injected and self.t-self.start>100:
            self.t+=31;self.gap_injected=True
        if self.case=='persistent_gap' and self.t-self.start>100:self.t+=31
        if self.case=='clock_rollback' and not self.gap_injected and self.t-self.start>100:
            self.t-=20;self.gap_injected=True
    def transient_once(self,name):
        if self.case=='once_'+name and not self.injected and self.t-self.start>100:
            self.injected=True;raise OSError(errno_values[name],'transient '+name)
    def observe(self):
        elapsed=self.t-self.start
        for name in errno_names:self.transient_once(name)
        if self.case=='persistent_enodata' and elapsed>100:
            raise OSError(errno_values['ENODATA'],'persistent ENODATA')
        if self.case=='nonretry_eio' and elapsed>100:
            raise OSError(errno.EIO,'actual sample unavailable')
        if self.case=='after_timeout_unavailable' and self.stops>0:
            raise OSError(errno_values['ENODATA'],'source unavailable after timeout')
        if self.case=='after_timeout_once_enodata' and self.stops>0 and not self.injected:
            self.injected=True;raise OSError(errno_values['ENODATA'],'one post-timeout ENODATA')
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
        if self.case=='recheck_not_timeout' and self.stops>0:seconds=35999;timeout=0
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
        if self.case=='IO_failure' and self.t-self.start>100:
            raise OSError('actual sample unavailable')
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
        self.auto_request_attempts+=1
        if self.case=='AUTO_IO_failure':raise OSError('AUTO sysfs write failed')
        self.auto=True
    def retry(self,phase,error,event):
        self.retry_calls+=1;self.auto_during_retry.append(self.auto)
    def retry_exhausted(self,phase,error,events):
        self.retry_exhausted_calls+=1


passing_cases={'success','one_gap','after_timeout_once_enodata'} | {'once_'+name for name in errno_names}
failing_cases={
    'initial_old','early_timeout','fast_counter','stalled_counter','counter_reset',
    'already_expired','AUTO_clears','Full','hot','low_voltage','stop_failure','not_stopped',
    'ordinary_fault','wrong_mode','IO_failure','cancel','persistent_gap','clock_rollback',
    'cleanup_failure','no_timeout','cancel_at_timeout','cancel_after_AUTO','AUTO_IO_failure',
    'validate_failure','persistent_enodata','nonretry_eio','after_timeout_unavailable',
    'recheck_not_timeout'}
cases=sorted(passing_cases|failing_cases)
results={}
for case in cases:
    io=IO(case);result=m.observe_timeout(io)
    assert result['passed']==(case in passing_cases),(case,result)
    assert io.stops>=1,(case,'cleanup was not attempted')
    if case=='success':
        assert result['observed_seconds']==35800 and result['initial_session_seconds']==200
        assert result['timeout_stop_verified'] and result['timeout_survived_auto'] and io.auto
        assert result['transient_retries']==0 and not result['retry_exhausted']
    if case.startswith('once_'):
        assert len(result['transient_events'])==1 and io.retry_calls==1,(case,result)
        assert not result['retry_exhausted'] and io.auto_during_retry==[False],(case,result)
        assert result['transient_events'][0]['errno']==errno_values[case[5:]],(case,result)
    if case=='one_gap':
        assert len(result['sample_gaps'])==1 and len(result['transient_events'])==1,(case,result)
        assert io.auto_during_retry==[False] and not result['retry_exhausted'],(case,result)
    if case=='after_timeout_once_enodata':
        assert io.auto_request_attempts==1 and io.auto and result['timeout_stop_verified'],(case,result)
        assert io.auto_during_retry==[False],(case,result)
    if case=='persistent_enodata':
        assert result['retry_exhausted'] and result['error'] and not io.auto,(case,result)
        assert io.retry_exhausted_calls==1 and io.retry_calls>1,(case,result)
        assert not any(io.auto_during_retry),(case,result)
    if case=='persistent_gap':
        assert result['retry_exhausted'] and result['sample_gaps'] and not io.auto,(case,result)
        assert not any(io.auto_during_retry),(case,result)
    if case=='nonretry_eio':
        assert result['error_type']=='OSError' and not io.retry_calls and not io.auto,(case,result)
    if case=='after_timeout_unavailable':
        assert result['retry_exhausted'] and not io.auto and io.auto_request_attempts==0,(case,result)
        assert result['timeout_stop_verified'] is False,(case,result)
        assert not any(io.auto_during_retry),(case,result)
    if case=='recheck_not_timeout':
        assert not io.auto and io.auto_request_attempts==0,(case,result)
        assert result['timeout_stop_verified'] is False,(case,result)
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
    results[case]=dict(passed=result['passed'],reason=result['reason'],error=result['error'],
        transient_retries=result['transient_retries'],retry_exhausted=result['retry_exhausted'],
        auto=io.auto,cleanup_error=result['cleanup_error'])

# Worker read gate: a source glitch may be retried, but AUTO is written only
# after a completely fresh timeout sample validates. Windows skips this because
# the real worker intentionally imports fcntl.
worker_tests=None
try:
    import fcntl
except ImportError:
    pass
else:
    from unittest.mock import patch
    worker_spec=importlib.util.spec_from_file_location(
        'worker_timeout_retry',Path(__file__).with_name('timeout-live-candidate')/'worker.py')
    worker=importlib.util.module_from_spec(worker_spec);worker_spec.loader.exec_module(worker)
    class FakePath:
        writes=[]
        def __init__(self,path):self.path=path
        def write_text(self,value):self.writes.append(value)
    valid=dict(boottime=1000.,register08=8,
        sample=dict(cycle_timeout=1,session_seconds=36000,error=-62))
    def auto_io(observe):
        io=worker.IO.__new__(worker.IO);clock=[1000.];saved=[];failures=[]
        io.now=lambda:clock[0]
        io.sleep=lambda seconds:clock.__setitem__(0,clock[0]+seconds)
        io.identity=lambda:None;io.observe=observe;io.validate=lambda value:None
        io.manager={'verify':lambda:'meta'};io.meta='meta'
        io.save=lambda name,value:saved.append((name,value))
        io.fail=lambda stage,error,value=None,partial=None,extra=None:failures.append(
            dict(stage=stage,error=repr(error),extra=extra))
        return io,clock,saved,failures
    FakePath.writes=[]
    calls=[0]
    def observe_once():
        calls[0]+=1
        if calls[0]==1:raise OSError(errno_values['ENODATA'],'one source glitch')
        assert FakePath.writes==[],'AUTO was written before the fresh retry sample'
        return valid
    io,clock,saved,failures=auto_io(observe_once)
    with patch.object(worker,'Path',FakePath):worker.IO.request_auto(io)
    assert FakePath.writes==['auto\n'] and calls[0]==2 and not failures
    assert {name for name,_ in saved}=={
        'heartbeat.json','transient-private.json','AUTO-after-timeout-request.json'}
    FakePath.writes=[]
    def observe_persistent():raise OSError(errno_values['ENODATA'],'persistent source glitch')
    io,clock,saved,failures=auto_io(observe_persistent)
    with patch.object(worker,'Path',FakePath):
        try:worker.IO.request_auto(io)
        except OSError:pass
        else:raise AssertionError('persistent ENODATA unexpectedly reached AUTO')
    assert FakePath.writes==[] and failures and failures[-1]['stage']=='retry_exhausted:request_auto'
    assert any(name=='heartbeat.json' for name,_ in saved)
    assert clock[0]-1000.==m.TRANSIENT_RETRY_SECONDS
    worker_tests=2

print(json.dumps({'control_tests_passed':True,'cases':len(cases),'worker_retry_tests':worker_tests,
    'hardware_tested':False,'results':results}))
