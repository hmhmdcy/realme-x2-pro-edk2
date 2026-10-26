"""Original one-shot RTC verification for the future timer-driver boot."""
from pathlib import Path
import argparse,ast,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=load('timer_pm_adapter',HERE/'host.py');post=load('timer_pm_postboot',HERE/'postboot.py');u=adapter.u
m=load('timer_pm_original_owner',HERE.parent/'usb-pm-notify-update/pm.py')
m.update=u;m.postboot=post;m.NAME='pm504-charger-timer-live-20261024-01'
m.REMOTE='/root/charging-management-20261023/'+m.NAME;m.GUARD=post.GUARD
def trace_source():
    raw=(HERE.parent/'pm504-wakeup-evidence/trace-worker.inc').read_bytes().replace(b'pm504-wakeup-live-20261024-03',m.NAME.encode())
    raw+=b'\n'+(HERE.parent/'usb-irq-wake-update/callback-trace.inc').read_bytes();ast.parse(raw);return raw
m.trace_source=trace_source
source=inspect.getsource(m.launch)
before="guard=Path(PACKET['guard']);assert not guard.parent.exists();guard.parent.mkdir(mode=0o700)\nsave(guard,(PACKET['boot_id']+'\\n').encode())"
source=u.replace(source,before,"guard=Path(PACKET['guard']);assert guard.read_bytes()==(PACKET['boot_id']+'\\n').encode()")
source=u.replace(source,'guard_created=True,boot_id=','guard_created=False,existing_guard_revalidated=True,boot_id=')
before="trace=(update.HERE.parent/'pm504-wakeup-evidence/trace-worker.inc').read_bytes().replace(b'pm504-wakeup-live-20261024-03',NAME.encode())"
source=u.replace(source,before,'trace=trace_source()')
exec(compile(source,'<original-one-shot-PM-with-existing-timer-boot-guard>','exec'),m.__dict__)
def check():
    assert post.collector()==(u.OUT/'postboot-collector-template.py').read_bytes();trace_source()
    return dict(prepared=True,PM_requested=False,device_accessed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='check',choices=['check','launch','fetch']);a=p.parse_args()
    print(json.dumps(check() if a.action=='check' else getattr(m,a.action)(),indent=2))
