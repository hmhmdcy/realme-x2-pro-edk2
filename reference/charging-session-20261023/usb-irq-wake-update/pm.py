"""One original PM owner plus filtered callback evidence for the USB driver."""
from pathlib import Path
import argparse,ast,base64,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('irq_wake_pm_adapter',HERE/'host.py');post=load('irq_wake_pm_postboot',HERE/'postboot.py');u=adapter.u
m=load('irq_wake_original_pm_owner',HERE.parent/'usb-pm-notify-update/pm.py')
m.update=u;m.postboot=post;m.NAME='pm504-usb-irq-wake-live-20261024-01';m.REMOTE='/root/charging-management-20261023/'+m.NAME;m.GUARD=post.GUARD
def trace_source():
 base=(HERE.parent/'pm504-wakeup-evidence/trace-worker.inc').read_bytes().replace(b'pm504-wakeup-live-20261024-03',m.NAME.encode())
 source=base+b'\n'+(HERE/'callback-trace.inc').read_bytes()
 ast.parse(source);return source
m.trace_source=trace_source
source=inspect.getsource(m.launch)
before="guard=Path(PACKET['guard']);assert not guard.parent.exists();guard.parent.mkdir(mode=0o700)\nsave(guard,(PACKET['boot_id']+'\\n').encode())"
after="guard=Path(PACKET['guard']);assert guard.read_bytes()==(PACKET['boot_id']+'\\n').encode()"
assert source.count(before)==1;source=source.replace(before,after)
assert source.count('guard_created=True,boot_id=')==1
source=source.replace('guard_created=True,boot_id=','guard_created=False,existing_guard_revalidated=True,boot_id=')
before="trace=(update.HERE.parent/'pm504-wakeup-evidence/trace-worker.inc').read_bytes().replace(b'pm504-wakeup-live-20261024-03',NAME.encode())"
assert source.count(before)==1;source=source.replace(before,'trace=trace_source()')
exec(compile(source,'<wake-callback-original-PM-launch>','exec'),m.__dict__)
def trace_check():
 before=u.request()['identity']['boot_id']
 prefix=b'from pathlib import Path\nimport hashlib,json,os,time\n'
 body=prefix+trace_source()+('NAME='+repr(m.NAME)+'\n').encode()+br'''
io=PMTraceFS(NAME);trace=PMScopedTrace(io)
try:
 trace.start()
finally:
 cleanup=trace.close()
assert not cleanup['cleanup_errors'] and not io.root.exists()
config=json.loads((io.out/'usb-callback-config-private.json').read_bytes())
assert set(config['enable_readbacks'].values())=={'1'}
print(json.dumps(dict(passed=True,trace_only=True,PM_requested=False,own_instance_removed=True,callback_filter=config['filter'])))
'''
 ast.parse(body)
 packet=dict(boot_id=before,root='/root/charging-management-20261023/usb-irq-wake-trace-check-20261024-01',source=base64.b64encode(body).decode(),sha256=u.sha(body))
 code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,runpy
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['boot_id']
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
raw=base64.b64decode(PACKET['source'],validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['sha256']
with (root/'worker.py').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
runpy.run_path(str(root/'worker.py'),run_name='__main__')
'''
 return u.call('trace-check',code,False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['trace-check','launch','fetch']);a=p.parse_args()
 print(json.dumps(trace_check() if a.action=='trace-check' else getattr(m,a.action)(),indent=2))
