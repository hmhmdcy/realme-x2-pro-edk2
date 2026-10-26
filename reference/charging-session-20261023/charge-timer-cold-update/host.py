"""Reuse owned SSH/supervision for a charger-only cold stage. Default local only."""
from pathlib import Path
import argparse,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=load('timer_cold_existing_ssh_owner',HERE.parent/'usb-irq-wake-update/host.py');u=adapter.u
PREVIOUS=u.OUT
u.OUT=u.BASE/'charge-timer-cold-update-live-20261024-01'
u.TX='irq-native-usb-pm-stage-timer-20261024-01';u.REMOTE='/root/charging-management-20261023/'+u.TX;u.LEAF=HERE
def check():
    request=u.request();derived=json.loads((HERE/'derivation.json').read_bytes());tested=json.loads((HERE/'test-result.json').read_bytes())
    assert derived['passed'] and tested['passed'] and len(tested['cases'])==5
    assert derived['worker_sha256']==tested['worker_sha256']==u.sha((HERE/'stage-worker.py').read_bytes())==request['worker_sha256']
    assert (u.BASE/'boot-adoption-private.json').read_bytes()==(u.OUT/'previous-pointer.json').read_bytes()
    worker=u.load(u.OUT/'stage-worker.py','timer_cold_local_contract');files,new=worker.unpack(request)
    assert set(files)=={worker.KO,worker.MANIFEST} and new['modules']['samurai-usb-input']['sha256']=='13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4'
    return dict(passed=True,device_accessed=False,stage_started=False)
def launch():
    check();source=inspect.getsource(u.launch)
    source=u.replace(source,"BASE/'usb-input-pm-notify-cohort-private-02/rollback-two-files.tar.gz'", "BASE/'charge-timer-hold-cohort-private-02/rollback-two-files.tar.gz'")
    scope=dict(u.__dict__);exec(compile(source,'<original-cold-stage-owned-launch>','exec'),scope)
    return scope['launch']()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='check',choices=['check','preflight','launch','fetch']);a=p.parse_args()
    if a.action in ['check','preflight']:check()
    print(json.dumps(check() if a.action=='check' else launch() if a.action=='launch' else getattr(u,a.action)(),indent=2))
