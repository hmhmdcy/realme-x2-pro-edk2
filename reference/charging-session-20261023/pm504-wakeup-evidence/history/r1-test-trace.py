"""Exercise actual scoped setup/cleanup and unchanged owned-worker composition."""
from pathlib import Path
import ast,copy,importlib.util,sys,time,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('pm504_scoped_evidence_builder',HERE/'host.py');builder=importlib.util.module_from_spec(s);s.loader.exec_module(builder)
fixture=builder.m.host.load(builder.m.host.DEVICE/'test-device.py','pm504_scoped_explicit_fixture')

class FakeIO:
    def __init__(self,bad_filter=False,cleanup_error=False):
        self.bad_filter=bad_filter;self.cleanup_error=cleanup_error;self.values={};self.writes=[];self.saved={};self.created=False;self.removed=False
    def mkdir(self):self.created=True
    def read(self,name):
        if name.endswith('wakeup_source_activate/format'):return 'field:__data_loc char[] name;\nfield:u64 state;'
        if name.endswith('suspend_resume/format'):return 'field:const char * action;\nfield:bool start;'
        if name=='trace_clock':return '[boot] local' if self.values.get(name)=='boot' else '[local] boot'
        if name.endswith('/filter') and self.bad_filter and self.values.get(name)!='0':return 'wrong filter'
        if name.endswith('/trigger') and name not in self.values:return '# Available triggers: stacktrace'
        return self.values.get(name,'0')
    def write(self,name,value):self.writes.append((name,value));self.values[name]=value
    def save(self,name,value):self.saved[name]=value
    def save_trace(self):
        if self.cleanup_error:raise OSError('modeled trace read failure')
        return dict(bytes=0,per_cpu={'cpu0':'overrun: 0\ncommit overrun: 0\ndropped events: 0'})
    def remove(self):self.removed=True

def namespace(io):
    raw,request=fixture.fixture('forward_504')
    packet=dict(schema='samurai-native-pm-smoke-v1',postboot_request=request,
                adoption_guard='/var/lib/samurai/irq-native-usb-pm-activate-model-adopted/boot-id-private.txt')
    code=builder.worker_code(packet);tree=ast.parse(code);tree.body=[n for n in tree.body if not isinstance(n,ast.If)]
    ns=dict(__name__='pm_scoped_model',__file__='/modeled/pm504-wakeup-live-20261024-02/worker.py')
    exec(compile(tree,'<actual-scoped-worker-model>','exec'),ns)
    class Reader:
        def __init__(self,value):self.value=str(value)
        def read_text(self):return request['new_boot_id']+'\n' if self.value==packet['adoption_guard'] else 'enabled\n'
        def resolve(self):return self
        @property
        def parent(self):return self
        @property
        def name(self):return 'pm504-wakeup-live-20261024-02'
    calls=[];ns['Path']=Reader;ns['identity']=lambda:copy.deepcopy(raw['identity_before'])
    ns['PMTraceFS']=lambda name:io;ns['pm_smoke_base']=lambda:calls.append('one original PM body') or 0
    return ns,calls

class ScopedChecks(unittest.TestCase):
    def test_success_cleanup_has_no_global_or_wakeup_policy_writes(self):
        io=FakeIO();ns,calls=namespace(io);self.assertEqual(ns['pm_smoke'](),0)
        self.assertEqual(calls,['one original PM body']);self.assertTrue(io.created and io.removed)
        self.assertIn(('events/power/wakeup_source_activate/trigger','!stacktrace'),io.writes)
        self.assertEqual(io.values['tracing_on'],'0')
        self.assertEqual(io.values['events/power/suspend_resume/enable'],'0')
        self.assertFalse(io.saved['trace-cleanup-private.json']['cleanup_errors'])
        self.assertTrue(all(not p.startswith('/') and '/wakeup' not in p.removeprefix('events/power') for p,_ in io.writes if not p.startswith('events/power')))

    def test_bad_readback_refuses_PM_and_preserves_primary_error(self):
        io=FakeIO(bad_filter=True,cleanup_error=True);ns,calls=namespace(io)
        with self.assertRaises(AssertionError):ns['pm_smoke']()
        self.assertEqual(calls,[]);self.assertTrue(io.removed)
        cleanup=io.saved['trace-cleanup-private.json']
        self.assertEqual(cleanup['cleanup_errors'][0]['phase'],'retain_trace')
        self.assertFalse(any(p.endswith('/enable') and v=='1' for p,v in io.writes))

    def test_actual_launcher_only_changes_namespace(self):
        # The actual original function still owns Popen, EOF and same-child wait.
        text=builder.source
        self.assertNotIn('pm504-smoke-live-20261024-01',text)
        self.assertIn('pm504-wakeup-live-20261024-02',text)
        self.assertIn('adopt.transfer(out,code,host,host.PEER)',text)
        tail=next(n.value for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Constant) and isinstance(n.value,bytes) and b'from pathlib import Path' in n.value)
        ast.parse(b'LAUNCH={}\n'+tail)

if __name__=='__main__':unittest.main()
