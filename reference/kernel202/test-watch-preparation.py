"""Exercise the production watcher with controlled DBus epochs and worker exits."""
from pathlib import Path
import importlib.util,json,sys,tempfile,types

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('assist202',here/'samurai-gnss-assist.py')
assist=importlib.util.module_from_spec(spec);spec.loader.exec_module(assist)
reports=[]

def scenario(name, timeline, jobs, end):
    clock=[0.0];handlers={};started=[];waited=[]
    def current():
        return next(value for tick,value in reversed(timeline) if clock[0]>=tick)
    class Properties:
        def Get(self, interface, name):
            assert name=='Enabled';return current()[1]
    class Manager:
        def GetManagedObjects(self):
            return {'/org/freedesktop/ModemManager1/Modem/0':{'org.freedesktop.ModemManager1.Modem.Location':{'SupportedAssistanceData':1}}}
    class Daemon:
        def GetNameOwner(self, service):return current()[0]
    class Bus:
        def name_has_owner(self,service):return current()[0] is not None
        def get_object(self,service,path):
            if service=='org.freedesktop.DBus':return Daemon()
            return Manager() if path=='/org/freedesktop/ModemManager1' else Properties()
        def close(self):pass
    class DBusException(Exception):pass
    fake_dbus=types.SimpleNamespace(SystemBus=lambda **kw:Bus(), Interface=lambda obj,_:obj, DBusException=DBusException)
    class Process:
        returncode=None
        def __init__(self, arguments, stdout, stderr):
            index=len(started);assert index<len(jobs),(name,arguments,started)
            kind='prepare' if arguments[-1]=='--prepare-time' else 'assist'
            if kind=='assist':assert arguments[-2:]==['--once','--active-only']
            expected, result, delay=jobs[index];assert kind==expected,(name,kind,expected)
            self.finish=clock[0]+delay;self.index=index
            stdout.write(json.dumps(result).encode());stdout.flush()
            started.append(dict(kind=kind,clock=clock[0],owner=current()[0]))
        def poll(self):
            if clock[0]<self.finish:return None
            self.returncode=0;return 0
        def wait(self):waited.append(self.index);self.returncode=0;return 0
    def sleep(seconds):
        clock[0]+=seconds
        if clock[0]>=end:handlers[15](15,None)
    old=(assist.time,assist.signal,assist.subprocess,sys.modules.get('dbus'))
    assist.time=types.SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep)
    assist.signal=types.SimpleNamespace(SIGTERM=15,SIGINT=2,signal=lambda n,fn:handlers.__setitem__(n,fn))
    assist.subprocess=types.SimpleNamespace(Popen=Process)
    sys.modules['dbus']=fake_dbus
    try:
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);directory.chmod(0o700)
            assist.watch(directory)
            state=json.loads((directory/'watch-state.json').read_text())
            assert not state['running'] and len(started)==len(jobs)
    finally:
        assist.time,assist.signal,assist.subprocess,prior=old
        if prior is None:sys.modules.pop('dbus',None)
        else:sys.modules['dbus']=prior
    reports.append(dict(name=name,started=started,waited=waited,passed=True))
    return state,started,waited

prepared={'status':'time-prepared'}
current_result={'status':'current'}
state,starts,_=scenario('idle preflight then one active worker',[(0,(':a',0)),(4,(':a',4)),(8,(':a',0))],[('prepare',prepared,1),('assist',current_result,1)],12)
assert state['time_prepared'] and state['time_preparation_completions']==state['worker_completions']==1
state,starts,_=scenario('unsynchronized clock retries in ten seconds',[(0,(':a',0))],[('prepare',{'status':'clock-not-synchronized'},1),('prepare',prepared,1)],18)
assert starts[1]['clock']-starts[0]['clock']==12 and state['time_prepared']
state,starts,_=scenario('late old owner completion cannot prepare new owner',[(0,(':a',0)),(2,(':b',0))],[('prepare',prepared,5),('prepare',prepared,1)],12)
assert starts[1]['owner']==':b' and starts[1]['clock']==6 and state['time_prepared']
state,starts,_=scenario('GPS racing preparation gets regular active worker',[(0,(':a',0)),(2,(':a',4))],[('prepare',{'status':'time-preparation-raced'},1),('assist',current_result,1)],8)
assert not state['time_prepared'] and state['worker_completions']==1
state,starts,waited=scenario('stop waits for in-flight UTC cleanup',[(0,(':a',0))],[('prepare',prepared,20)],2)
assert waited==[0]
state,starts,_=scenario('already active GPS never receives idle preflight',[(0,(':a',4)),(6,(':a',0))],[('assist',current_result,1),('prepare',prepared,1)],12)
assert [entry['kind'] for entry in starts]==['assist','prepare'] and state['time_prepared']
for status,delay in [('current',3600),('refreshed',3600),('clock-not-synchronized',10),('time-preparation-raced',10),('modem-owner-changed',10),('download-failed',600)]:
    assert assist.retry_seconds({'status':status})==delay
report=dict(stage=202,production_watch_scenarios=reports,retry_status_cases=6,all_passed=True,hardware_qmi_not_simulated_as_hardware_success=True)
(here/'watch-preparation-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=202,production_watch_scenarios=len(reports),retry_status_cases=6,all_passed=True)))
