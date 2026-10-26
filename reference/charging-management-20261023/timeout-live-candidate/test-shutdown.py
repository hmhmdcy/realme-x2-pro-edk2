"""Actual detector/cancellation/join logic against process fixtures; no shutdown."""
from pathlib import Path
import fcntl,hashlib,importlib.util,json,os,signal,tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
d=load('actual_shutdown_detector',HERE/'shutdown-observer.py')
w=load('actual_shutdown_worker',HERE/'worker.py')
s=load('actual_shutdown_supervisor',HERE/'supervisor.py')
exercise=load('actual_timeout_observer',HERE.parent/'timeout-observation.py')
cases=0
with tempfile.TemporaryDirectory(prefix='samurai-shutdown-fixture-') as temporary:
    root=Path(temporary);binary=root/'openrc';binary.write_bytes(b'fixture executable identity');binary.chmod(0o755)
    other=root/'other-openrc';other.write_bytes(binary.read_bytes());other.chmod(0o755)
    def process(where,argv=b'/sbin/openrc\0shutdown\0',uid='0',state='S',exe=None):
        proc=root/where;entry=proc/'77';entry.mkdir(parents=True)
        (entry/'cmdline').write_bytes(argv)
        (entry/'status').write_text('Uid:\t'+'\t'.join([uid]*4)+'\n')
        fields=[state]+['0']*18+['12345']
        (entry/'stat').write_text('77 (openrc) '+' '.join(fields)+'\n')
        (entry/'exe').symlink_to(exe or binary)
        return proc
    fixtures=[('shutdown',{},True),('nonroot',dict(uid='10000'),False),
        ('wrong_binary',dict(exe=other),False),('zombie',dict(state='Z'),False),
        ('default',dict(argv=b'/sbin/openrc\0default\0'),False),
        ('wrong_name',dict(argv=b'/bin/other\0shutdown\0'),False),
        ('extra_arg',dict(argv=b'/sbin/openrc\0shutdown\0anything\0'),False),
        ('empty',dict(argv=b''),False)]
    for name,kwargs,expected in fixtures:
        p=process(name,**kwargs);answer=d.pending_openrc_shutdown(p,binary)
        assert bool(answer)==expected,name
        if expected:assert answer==dict(action='openrc_shutdown',pid=77,startticks=12345)
        cases+=1
    p=process('recycled_pid');original_read=Path.read_text;reads=[0]
    def recycled(path,*args,**kwargs):
        value=original_read(path,*args,**kwargs)
        if path==p/'77/stat':
            reads[0]+=1
            if reads[0]==2:value=value.replace('12345','12346')
        return value
    with patch.object(Path,'read_text',recycled):assert d.pending_openrc_shutdown(p,binary) is None
    cases+=1
    valid=root/'shutdown'
    saved={};io=w.IO.__new__(w.IO);io.now=lambda:1000.;io.save=lambda n,v:saved.update({n:v})
    with patch.object(w.shutdown,'pending_openrc_shutdown',lambda:d.pending_openrc_shutdown(valid,binary)):
        assert io.cancelled() is True
    assert saved['shutdown-observed.json']['startticks']==12345
    cases+=1
    class Child:
        def __init__(self):self.pid=os.getpid();self.code=None;self.signals=[]
        def poll(self):return self.code
        def send_signal(self,value):self.signals.append(value);self.code=0
        def terminate(self):self.send_signal(signal.SIGTERM)
        def wait(self,timeout=None):self.code=0;return 0
        @property
        def returncode(self):return self.code
    lockpath=root/'charging.lock';lockpath.touch(mode=0o600)
    io.parts=[Child(),Child()];io.load_closed=False;io.lock=os.open(lockpath,os.O_RDWR)
    fcntl.flock(io.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    sample=dict(cell1_uv=3800000,cell2_uv=3803000,temp_decic=250,logical_full=0,full_holding=0,
        full_cause=0,session_seconds=200,cycle_timeout=0,latched=0,error=0,stop_error=0,desired_enable=1)
    class FixtureIO:
        def now(self):return 1000.
        def observe(self):return dict(boottime=1000.,behaviour='auto',register08=0x10,sample=dict(sample))
        def validate(self,value):pass
        def record(self,phase,value):pass
        def cancelled(self):return w.IO.cancelled(io)
        def stop_load(self):w.IO.stop_load(io)
        def balance(self,value):raise AssertionError('load balancing continued after shutdown')
    with patch.object(w.shutdown,'pending_openrc_shutdown',lambda:d.pending_openrc_shutdown(valid,binary)):
        result=exercise.observe_timeout(FixtureIO())
    assert result['reason']=='cancelled' and not result['passed'] and result['load_joined']
    assert result['error'] is result['cleanup_error'] is None
    assert all(c.signals==[signal.SIGTERM] for c in io.parts)
    with lockpath.open('r+b') as probe:
        try:fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise AssertionError('lock was not owned before normal close')
        io.close();fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert io.lock is None
    cases+=1
    supervised=root/'supervisor';supervised.mkdir()
    child=Child()
    with patch.object(s,'HERE',supervised),patch.object(s.sys,'argv',['supervisor.py','--execute']),\
         patch.object(s.subprocess,'Popen',return_value=child),\
         patch.object(s.shutdown,'pending_openrc_shutdown',lambda:d.pending_openrc_shutdown(valid,binary)):
        rc=s.main()
    terminal=json.loads((supervised/'supervisor-terminal.json').read_bytes())
    assert rc==0 and child.signals==[signal.SIGTERM] and terminal['child_joined']
    assert terminal['fresh_IO_skipped_for_shutdown'] and terminal['after'] is None
    assert terminal['watchdog_reason']=='system_shutdown' and terminal['helpers_ended']
    cases+=1
    # A completed child may bypass the loop just as shutdown begins.
    late=root/'late-shutdown';late.mkdir();child=Child();child.code=0
    with patch.object(s,'HERE',late),patch.object(s.sys,'argv',['supervisor.py','--execute']),\
         patch.object(s.subprocess,'Popen',return_value=child),\
         patch.object(s.shutdown,'pending_openrc_shutdown',lambda:d.pending_openrc_shutdown(valid,binary)):
        assert s.main()==0
    terminal=json.loads((late/'supervisor-terminal.json').read_bytes())
    assert terminal['fresh_IO_skipped_for_shutdown'] and not child.signals
    assert terminal['after'] is None and terminal['watchdog_reason']=='system_shutdown'
    cases+=1
result=dict(passed=True,cases=cases,actual_detector_and_cancel_methods_exercised=True,
    actual_observer_cancel_and_join_exercised=True,actual_supervisor_shutdown_path_exercised=True,
    actual_local_flock_release_verified=True,real_system_shutdown_tested=False,phone_accessed=False,
    source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in
        ['shutdown-observer.py','worker.py','supervisor.py','test-shutdown.py']})
(HERE/'shutdown-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
