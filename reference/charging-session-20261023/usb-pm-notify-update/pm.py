"""One traced RTC-backed suspend attempt using the original tested primitive."""
from pathlib import Path
import ast,base64,importlib.util,json,sys
sys.dont_write_bytecode=True
def load(name,file):
 s=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parent/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
update=load('notify_pm_update','host.py');postboot=load('notify_pm_postboot','postboot.py')
NAME='pm504-notify-live-20261024-01';REMOTE='/root/charging-management-20261023/'+NAME
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-notify-20261024-01-adopted/boot-id-private.txt'
def launch():
 checked=json.loads((update.OUT/'postboot-reviewed.json').read_bytes());update.need(checked['passed'] and len(checked['checks'])==12 and not checked['errors'],'twelve actual postboot checks')
 request=json.loads((update.OUT/'postboot-request.json').read_bytes());source=(update.OUT/'postboot-collector.py').read_bytes()
 update.need(source==postboot.collector(),'actual collector changed')
 primitive=(update.HERE.parent/'pm-current-evidence-candidate/pm-transaction.py').read_bytes()
 update.need(update.sha(primitive)=='fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1','original tested PM transaction')
 old=(update.POST/'pm-smoke-worker.inc').read_bytes();body,entry=old.split(b"\nif __name__=='__main__':",1)
 body=update.replace(body.decode(),'def pm_smoke():','def pm_smoke_base():').encode()
 trace=(update.HERE.parent/'pm504-wakeup-evidence/trace-worker.inc').read_bytes().replace(b'pm504-wakeup-live-20261024-03',NAME.encode())
 pm_request=dict(schema='samurai-native-pm-smoke-v1',postboot_request=request,adoption_guard=GUARD)
 worker=('PM_REQUEST='+repr(pm_request)+'\n').encode()+source+b'\n'+primitive+b'\n'+body+b'\n'+trace+b"\nif __name__=='__main__':"+entry
 supervisor=(update.POST/'pm-smoke-supervisor.py').read_bytes();ast.parse(worker)
 update.create(update.OUT/'pm-worker.py',worker)
 packet=dict(root=REMOTE,boot_id=request['new_boot_id'],guard=GUARD,worker=base64.b64encode(worker).decode(),worker_sha256=update.sha(worker),supervisor=base64.b64encode(supervisor).decode(),supervisor_sha256=update.sha(supervisor))
 code=('PACKET='+repr(packet)+'\nREQUEST='+repr(request)+'\n').encode()+source+br'''
raw={};collect(REQUEST,raw);fresh=audit(raw,REQUEST)
assert fresh['passed'] and len(fresh['checks'])==12 and not fresh['errors']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['boot_id']
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077)
def save(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
guard=Path(PACKET['guard']);assert not guard.parent.exists();guard.parent.mkdir(mode=0o700)
save(guard,(PACKET['boot_id']+'\n').encode())
root.mkdir(mode=0o700)
for name,key in [('worker.py','worker'),('supervisor.py','supervisor')]:
 value=base64.b64decode(PACKET[key],validate=True);assert sha(value)==PACKET[key+'_sha256'];save(root/name,value)
save(root/'fresh-adoption-private.json',(json.dumps(fresh,indent=2)+'\n').encode())
save(root/'launch-private.json',(json.dumps(dict(boot_id=PACKET['boot_id'],worker_sha256=PACKET['worker_sha256']))+'\n').encode())
with (root/'supervisor-stdout-private.txt').open('xb') as out,(root/'supervisor-stderr-private.txt').open('xb') as err:
 child=subprocess.Popen([sys.executable,'-B',str(root/'supervisor.py'),'--supervise',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split();receipt=dict(pid=child.pid,startticks=int(fields[19]),argv=[v.decode() for v in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0])) if v])
 save(root/'supervisor-launch-private.json',(json.dumps(receipt)+'\n').encode())
print(json.dumps(dict(launched=True,supervisor=receipt,guard_created=True,boot_id=PACKET['boot_id'],fresh_twelve_passed=True)))
'''
 return update.call('pm-launch',code,False)
def fetch():
 code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json
root=Path(REMOTE);files={}
for p in root.iterdir():
 if p.is_file():
  raw=p.read_bytes();assert len(raw)<4000000;files[p.name]=dict(sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
print(json.dumps(dict(files=files)))
'''
 reply=update.call('pm-fetch',code);out=update.OUT/'pm-raw';out.mkdir(mode=0o700)
 for name,row in reply['files'].items():
  raw=base64.b64decode(row['base64'],validate=True);update.need(update.sha(raw)==row['sha256'],'raw bytes');update.create(out/name,raw)
 return dict(result=json.loads((out/'result-private.json').read_bytes()) if (out/'result-private.json').exists() else None,
  terminal=json.loads((out/'worker-terminal-private.json').read_bytes()) if (out/'worker-terminal-private.json').exists() else None,
  failure=(out/'failure-private.txt').read_text() if (out/'failure-private.txt').exists() else None)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','fetch']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
