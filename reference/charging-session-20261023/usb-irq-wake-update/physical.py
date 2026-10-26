"""One human-coordinated USB wake window; no device action on import/prepare."""
from pathlib import Path
import argparse,ast,base64,importlib.util,json,secrets,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wake_window_pm',HERE/'pm.py')
pm=importlib.util.module_from_spec(spec);spec.loader.exec_module(pm);u=pm.u
NAME='pm504-usb-physical-wake-20261024-01';REMOTE='/root/charging-management-20261023/'+NAME
LOCAL=u.OUT/'physical-window';u.OUT=LOCAL

def prepare():
    request=json.loads((LOCAL.parent/'postboot-request.json').read_bytes())
    result=json.loads((u.ROOT/'reference/charging-management-20261023/usb-irq-wake-rtc001-result.json').read_bytes())
    assert result['passed'] and result['boot_id']==request['new_boot_id'] and result['USB_suspend_resume_callbacks_returned0']
    assert (u.BASE/'boot-adoption-private.json').read_bytes()==(LOCAL.parent/'adoption-pointer-after-pm.json').read_bytes()
    assert not LOCAL.exists();LOCAL.mkdir(mode=0o700)
    primitive=(HERE.parent/'pm-current-evidence-candidate/pm-transaction.py').read_bytes()
    assert u.sha(primitive)=='fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1'
    trace=pm.trace_source().replace(pm.m.NAME.encode(),NAME.encode())
    packet=dict(postboot_request=request,adoption_guard=pm.post.GUARD)
    worker=('PM_REQUEST='+repr(packet)+'\n').encode()+(LOCAL.parent/'postboot-collector.py').read_bytes()+b'\n'+primitive+b'\n'+trace+b'\n'+(HERE/'physical-worker.inc').read_bytes()
    ast.parse(worker);compile(worker,'<physical-usb-wake-window>','exec')
    u.create(LOCAL/'worker.py',worker)
    u.save(LOCAL/'request.json',dict(remote=REMOTE,boot_id=request['new_boot_id'],worker_sha256=u.sha(worker),
                                   own_RTC_fallback_seconds=60,mem_write_limit=1,physical_test_started=False))
    return dict(prepared=True,device_accessed=False,physical_test_started=False)

def launch():
    request=json.loads((LOCAL/'request.json').read_bytes());worker=(LOCAL/'worker.py').read_bytes()
    assert u.sha(worker)==request['worker_sha256']
    supervisor=(u.POST/'pm-smoke-supervisor.py').read_bytes()
    packet=dict(root=REMOTE,boot_id=request['boot_id'],worker=base64.b64encode(worker).decode(),worker_sha256=u.sha(worker),
                supervisor=base64.b64encode(supervisor).decode(),supervisor_sha256=u.sha(supervisor),guard=pm.post.GUARD)
    code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['boot_id']
assert Path(PACKET['guard']).read_text()==PACKET['boot_id']+'\n'
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
def save(name,raw):
 with (root/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
for name,key in [('worker.py','worker'),('supervisor.py','supervisor')]:
 raw=base64.b64decode(PACKET[key],validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET[key+'_sha256'];save(name,raw)
save('launch-private.json',(json.dumps(dict(boot_id=PACKET['boot_id'],worker_sha256=PACKET['worker_sha256']))+'\n').encode())
with (root/'supervisor-stdout-private.txt').open('xb') as out,(root/'supervisor-stderr-private.txt').open('xb') as err:
 child=subprocess.Popen([sys.executable,'-B',str(root/'supervisor.py'),'--supervise',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 receipt=dict(pid=child.pid,startticks=int(fields[19]),argv=[x.decode() for x in Path('/proc',str(child.pid),'cmdline').read_bytes().split(b'\0') if x])
 save('supervisor-launch-private.json',(json.dumps(receipt)+'\n').encode())
print(json.dumps(dict(launched=True,supervisor=receipt,PM_requested=False,waiting_for_explicit_start=True)))
'''
    return u.call('launch',code,False)

def status():
    code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import json,time
root=Path(REMOTE);result={}
for name in ['ready-private.json','go-private.json','expired-private.json','worker-terminal-private.json','result-private.json']:
 if (root/name).exists():result[name]=json.loads((root/name).read_bytes())
if (root/'failure-private.txt').exists():result['failure']=(root/'failure-private.txt').read_text()
result['monotonic']=time.monotonic()
print(json.dumps(result))
'''
    return u.call('status-'+secrets.token_hex(3),code)

def start():
    code=('REMOTE='+repr(REMOTE)+'\nBOOT='+repr(json.loads((LOCAL/'request.json').read_bytes())['boot_id'])+'\n').encode()+br'''
from pathlib import Path
import json,os,time
root=Path(REMOTE);ready=json.loads((root/'ready-private.json').read_bytes())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==ready['boot_id']==BOOT
assert not (root/'worker-terminal-private.json').exists() and not (root/'expired-private.json').exists()
assert 0<=time.monotonic()-ready['monotonic']<200
with (root/'go-private.json').open('x') as f:
 json.dump(dict(boot_id=BOOT,monotonic=time.monotonic()),f);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(started=True,enter_mem_after_seconds=12,RTC_fallback_seconds=60,mem_write_limit=1)))
'''
    return u.call('start',code,False)

def fetch():
    code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json
root=Path(REMOTE);assert (root/'worker-terminal-private.json').exists();files={}
for p in root.iterdir():
 if p.is_file():
  raw=p.read_bytes();assert len(raw)<4000000
  files[p.name]=dict(sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
print(json.dumps(dict(files=files)))
'''
    reply=u.call('fetch',code);out=LOCAL/'raw';out.mkdir(mode=0o700)
    for name,row in reply['files'].items():
        assert Path(name).name==name
        raw=base64.b64decode(row['base64'],validate=True);assert u.sha(raw)==row['sha256'];u.create(out/name,raw)
    return dict(terminal=json.loads((out/'worker-terminal-private.json').read_bytes()),
                result=json.loads((out/'result-private.json').read_bytes()) if (out/'result-private.json').exists() else None,
                failure=(out/'failure-private.txt').read_text() if (out/'failure-private.txt').exists() else None)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','launch','status','start','fetch'])
    a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
