"""Exercise the actual worker's CPU-control and join methods; no phone access."""
from pathlib import Path
import importlib.util,json,os,subprocess
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('timer_worker',Path(__file__).with_name('worker.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


class Child:
    def __init__(self,exit_code=None,timeout=False):
        self.pid=os.getpid();self.code=exit_code;self.timeout=timeout;self.signals=[]
    def poll(self):return self.code
    def terminate(self):self.signals.append('TERM')
    def wait(self,timeout=None):
        if self.timeout:self.timeout=False;raise subprocess.TimeoutExpired('owned-child',timeout)
        self.code=0;return 0
    def kill(self):self.signals.append('KILL')
    @property
    def returncode(self):return self.code


def make():
    io=w.IO.__new__(w.IO);io.parts=[Child(),Child()];io.load_closed=False;io.duty=.15;io.ema=None
    io.deadline=100000;io.now=lambda:1000;io.saved={};io.save=lambda n,v:io.saved.update({n:v})
    return io
def value(current=0,temp=300,soc=45,cell=3800000):
    return dict(capacity=soc,sample=dict(gauge_current_ua=current,temp_decic=temp,cell1_uv=cell,cell2_uv=cell))
io=make();before=io.duty;io.balance(value(100000));assert io.duty>before
io=make();before=io.duty;io.balance(value(-100000));assert io.duty<before
io=make()
for _ in range(100):io.balance(value(1000000))
assert io.duty==.3
for _ in range(100):io.balance(value(-1000000))
assert io.duty==0
for case in [dict(temp=340),dict(temp=350),dict(soc=25),dict(cell=3600000)]:
    io=make();io.duty=.3;io.balance(value(100000,**case))
    assert io.duty==(.1 if case==dict(temp=340) else 0)
io=make();io.balance(value(soc=30));assert io.saved['cpu-load-control.json']['target_ua']==10000
io=make();io.balance(value(soc=60));assert io.saved['cpu-load-control.json']['target_ua']==-10000
io=make();io.parts[0].code=0
try:io.balance(value())
except (AssertionError,RuntimeError):pass
else:raise AssertionError('early child exit accepted')
io=make();parts=io.parts.copy();io.stop_load();io.stop_load()
assert all(p.signals==['TERM'] for p in parts) and io.saved['cpu-load-terminal.json']['all_joined']
io=make();io.parts[0].timeout=True;parts=io.parts.copy();io.stop_load()
assert parts[0].signals==['TERM','KILL'] and parts[1].signals==['TERM']
io=make();io.parts[0].code=7;p=io.parts[0];io.stop_load();assert not p.signals
# Launch setup failure after a first owned child must join that child. Only
# subprocess and affinity boundaries are mocked, not the worker methods.
io=make();io.parts=[];child=Child();calls=0
def start(*args,**kwargs):
    global calls
    calls+=1
    if calls==2:raise OSError('second child launch failed')
    return child
class Output:
    def __enter__(self):return None
    def __exit__(self,*args):pass
original_open=Path.open
def opened(path,*args,**kwargs):
    return Output() if path.name.startswith('cpu') and path.suffix=='.stderr' else original_open(path,*args,**kwargs)
with patch.object(w.os,'sched_getaffinity',return_value={4,7}),patch.object(w.subprocess,'Popen',side_effect=start),patch.object(Path,'open',opened):
    try:io.balance(value())
    except OSError:pass
    else:raise AssertionError('launch failure accepted')
assert io.load_closed and child.signals==['TERM']
print(json.dumps(dict(passed=True,groups=6,scope='actual balance/stop_load methods; process/affinity boundaries mocked',phone_accessed=False)))
