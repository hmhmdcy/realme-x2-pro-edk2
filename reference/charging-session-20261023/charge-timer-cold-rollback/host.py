"""Default local checks. Fresh original-key probe is required before dispatch."""
from pathlib import Path
import argparse,ast,base64,importlib.util,inspect,json,secrets,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=load('timer_rollback_existing_transport',HERE.parent/'charge-timer-cold-update/host.py');u=adapter.u
u.OUT=u.BASE/'charge-timer-cold-rollback-live-20261024-01'
u.TX='charger-timer-cold-rollback-20261024-01';u.REMOTE='/root/charging-management-20261023/'+u.TX
def worker():return load('current_timer_rollback_contract',HERE/'restore-worker.py')
def check():
    d=json.loads((HERE/'derivation.json').read_bytes());t=json.loads((HERE/'test-result.json').read_bytes())
    assert d['passed'] and t['passed'] and d['worker_sha256']==t['worker_sha256']==u.sha((HERE/'restore-worker.py').read_bytes())
    for path in HERE.glob('*.py'):ast.parse(path.read_bytes())
    return dict(passed=True,device_accessed=False,rollback_started=False)
def prepare():
    check();assert not u.OUT.exists();u.OUT.mkdir(mode=0o700)
    u.create(u.OUT/'restore-worker.py',(HERE/'restore-worker.py').read_bytes())
    inverse=(u.BASE/'charge-timer-hold-cohort-private-02/rollback-two-files.tar.gz').read_bytes();assert u.sha(inverse)==worker().ROLLBACK_PAYLOAD
    u.create(u.OUT/'rollback-two-files.tar.gz',inverse)
    return dict(prepared=True,device_accessed=False,request_created=False)
def probe_source(parameters):
    source=(HERE/'restore-worker.py').read_bytes();tail=b"\nif __name__=='__main__':raise SystemExit(main())\n"
    assert source.endswith(tail);source=source[:-len(tail)]
    code=('PARAMETERS='+repr(parameters)+'\n').encode()+source+b'\n'+(HERE/'probe-body.py.inc').read_bytes();ast.parse(code);return code
def audit_probe(reply):
    m=worker();r=reply['request'];m.unpack(r)
    assert reply['passed'] and reply['eligible'] and reply['read_only'] and not reply['phone_directory_or_lease_created']
    assert r['transaction_id']==u.TX and r['worker_sha256']==u.sha((HERE/'restore-worker.py').read_bytes())
    raws={}
    for name,row in reply['source_raws'].items():
        raw=base64.b64decode(row['base64'],validate=True);assert u.sha(raw)==row['sha256'];raws[name]=raw
    assert m.verify_source_records(r,raws,reply['source_process_observations'])==reply['source_proof']
    m.validate_profile(r,reply['current'])
    # Freshness is rechecked on the device at execution; never compare its
    # BOOTTIME against the host's clock or re-label this as a full postboot pass.
    m.safe_electrical(reply['snapshot'],reply['snapshot']['read_end']+.001);m.idle(reply['snapshot'])
    assert reply['snapshot']['notes']==m.expected_profile(r)['notes']
    assert reply['snapshot']['current_cache']==r['current_cache']==reply['current']['current_cache']
    return r
def preflight():
    check();assert (u.OUT/'restore-worker.py').read_bytes()==(HERE/'restore-worker.py').read_bytes()
    inverse=(u.OUT/'rollback-two-files.tar.gz').read_bytes()
    parameters=dict(transaction_id=u.TX,worker_sha256=u.sha((HERE/'restore-worker.py').read_bytes()),lease_token=secrets.token_hex(24),payload_base64=base64.b64encode(inverse).decode())
    reply=u.call('preflight',probe_source(parameters));r=audit_probe(reply)
    pointer=(u.BASE/'boot-adoption-private.json').read_bytes();current=json.loads(pointer);m=worker()
    assert (current['boot_id']==m.SOURCE_IDENTITY['boot_id'] and current['charging_manifest_sha256']==m.OLD_FILES[m.MANIFEST]) or (current['boot_id']==r['identity']['boot_id'] and current['charging_manifest_sha256'] in [m.OLD_FILES[m.MANIFEST],m.NEW_FILES[m.MANIFEST]])
    u.create(u.OUT/'previous-pointer.json',pointer)
    u.save(u.OUT/'request-private.json',r)
    return dict(passed=True,eligible=True,profile=r['profile'],read_only=True,lease_created=False)
def request():
    r=json.loads((u.OUT/'request-private.json').read_bytes())
    assert (u.OUT/'restore-worker.py').read_bytes()==(HERE/'restore-worker.py').read_bytes() and r['worker_sha256']==u.sha((HERE/'restore-worker.py').read_bytes())
    worker().unpack(r);return r
u.request=request
def launch():
    check();r=request();reply=json.loads((u.OUT/'preflight/reply.json').read_bytes());assert audit_probe(reply)==r
    source=inspect.getsource(u.launch)
    source=u.replace(source,"sys.argv=['stage','--execute-stage']","sys.argv=['restore','--execute-rollback']")
    source=source.replace('stage-worker.py','restore-worker.py')
    source=u.replace(source,"BASE/'usb-input-pm-notify-cohort-private-02/rollback-two-files.tar.gz'","BASE/'charge-timer-hold-cohort-private-02/rollback-two-files.tar.gz'")
    scope=dict(u.__dict__);exec(compile(source,'<original-owned-restore-dispatch>','exec'),scope);return scope['launch']()
def fetch():
    source=u.replace(inspect.getsource(u.fetch),"out/'device-stage/result.json'","out/'device-rollback/result.json'")
    scope=dict(u.__dict__);exec(compile(source,'<original-owned-restore-fetch>','exec'),scope);return scope['fetch']()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='check',choices=['check','prepare','preflight','launch','fetch']);a=p.parse_args()
    print(json.dumps(globals()[a.action](),indent=2))
