"""Exercise the actual bounded proof harness, local lock and worker methods."""
from pathlib import Path
import fcntl,hashlib,importlib.util,json,os,tempfile
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
proof=load('actual_reboot_proof',HERE/'shutdown-reboot-proof.py')
worker=load('actual_reboot_cancel_worker',HERE/'worker.py')
cases=[]
with tempfile.TemporaryDirectory(prefix='samurai-reboot-proof-') as temporary:
    for name in ['shutdown','deadline','read_error','owner_busy','stale_event']:
        root=Path(temporary)/name;root.mkdir();lock=root/'charging.lock';lock.touch(mode=0o600)
        clock=[1000.]
        if name=='stale_event':
            (root/'cancel').touch()
            (root/'shutdown-observed.json').write_text(json.dumps(dict(action='openrc_shutdown',boottime=1)))
        def detector():
            if name=='read_error':raise OSError('fixture /proc read unavailable')
            return dict(action='openrc_shutdown',pid=77,startticks=10) if name=='shutdown' else None
        occupied=lock.open('r+b') if name=='owner_busy' else None
        if occupied:fcntl.flock(occupied,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with patch.object(worker,'HERE',root),patch.object(worker.shutdown,'pending_openrc_shutdown',detector):
            result=proof.observe_shutdown(worker,'original',lambda:'original',lambda:clock[0],
                lambda amount:clock.__setitem__(0,clock[0]+amount),str(lock))
        assert result['passed']==(name=='shutdown'),(name,result)
        assert result['service_lock_released'] and result['helper_control_writes']==0
        assert not result['CPU_load_started']
        if name=='deadline':assert clock[0]==1030. and result['reason']=='thirty_second_deadline'
        if name in ['owner_busy','read_error']:assert result['error']
        if occupied:occupied.close()
        with lock.open('r+b') as verify:fcntl.flock(verify,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cases.append(name)
result=dict(passed=True,cases=cases,actual_harness_and_worker_methods=True,
    actual_local_flock=True,phone_accessed=False,real_reboot_tested=False,
    sources={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
        ['shutdown-reboot-proof.py','worker.py','shutdown-observer.py','test-shutdown-reboot-proof.py']})
(HERE/'shutdown-reboot-proof-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
