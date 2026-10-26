"""Exercise only the new trace filter cleanup; no phone or PM operation."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('physical_trace_test_pm',HERE/'pm.py')
pm=importlib.util.module_from_spec(spec);spec.loader.exec_module(pm)
scope=dict(Path=Path,os=os,json=json,time=time,hashlib=hashlib)
exec(compile(pm.trace_source(),'<actual-base-trace>','exec'),scope)
source=(HERE/'physical-worker.inc').read_text()
nodes=[n for n in ast.parse(source).body if isinstance(n,ast.ClassDef)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-new-trace-classes>','exec'),scope)

class FakeIO:
    def __init__(self,out,failure):
        self.out=out;self.root=out/'instance';self.failure=failure;self.failed=False;self.saved={};self.values={}
    def mkdir(self):self.root.mkdir()
    def read(self,name):
        if name.endswith('/format'):
            if '/irq/' in name:return 'field:int irq;'
            if 'device_pm_callback' in name:return 'field:__data_loc char[] driver;\nfield:int error;'
            if 'wakeup_source_activate' in name:return 'field:__data_loc char[] name;\nfield:u64 state;'
            return 'field:const char * action;\nfield:bool start;'
        if name=='trace_clock':return '[boot] mono'
        if name.endswith('/trigger'):return self.values.get(name,'# stacktrace')
        return self.values.get(name,'0')
    def write(self,name,value):
        self.values[name]=value
        if name==self.failure and value!='0' and not self.failed:
            self.failed=True;raise OSError('injected failure after write')
    def save(self,name,value):self.saved[name]=value
    def extra_save(self,name,value):self.saved[name]=value
    def save_trace(self):return dict(bytes=0,sha256=hashlib.sha256(b'').hexdigest(),per_cpu={})
    def remove(self):self.root.rmdir()

cases=[]
with tempfile.TemporaryDirectory(prefix='samurai-usb-physical-trace-') as temp:
    for index,failure in enumerate([None,'events/irq/irq_handler_entry/filter','events/irq/irq_handler_entry/enable']):
        out=Path(temp)/str(index);out.mkdir();io=FakeIO(out,failure)
        trace=scope['PhysicalScopedTrace'](io,{227,229});error=None
        try:trace.start()
        except OSError as caught:error=str(caught)
        finally:cleanup=trace.close()
        assert (error is not None)==(failure is not None)
        assert not cleanup['cleanup_errors'] and not io.root.exists()
        assert io.values['tracing_on']=='0'
        if trace.irq_filter:assert io.values['events/irq/irq_handler_entry/filter']=='0'
        if trace.irq_enabled:assert io.values['events/irq/irq_handler_entry/enable']=='0'
        assert all(value=='0' for name,value in io.values.items() if name.endswith('/enable'))
        cases.append(dict(injected_failure=failure,own_instance_removed=True,own_events_disabled=True))
result=dict(passed=True,scope='actual new trace classes with modeled filesystem',cases=cases,
            physical_worker_sha256=hashlib.sha256(source.encode()).hexdigest(),
            phone_accessed=False,PM_requested=False,physical_wakeup_accepted=False)
with (HERE/'physical-trace-test-result.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False)))
