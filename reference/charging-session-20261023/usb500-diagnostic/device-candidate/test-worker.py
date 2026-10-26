"""Actual candidate functions and frozen r6 gates; no network/device actions."""
from pathlib import Path
from unittest.mock import patch
import ast
import copy
import importlib.util
import json
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2] / 'charging-management-20261023'
spec = importlib.util.spec_from_file_location('usb500_worker', HERE / 'worker.py')
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
receipt = json.loads((MAIN / 'r6-update-result.json').read_text())
assert receipt['passed'] and receipt['new_manifest_sha256'] == w.r6.NEW
sample_fixture = receipt['sample']
assert 'session_seconds' in sample_fixture and 'logical_full' in sample_fixture
config = {'transaction': w.TX, 'host_trigger_nonce': 'a' * 48}


class Fake:
    def __init__(self, failures=(), full=False, accepts500=True):
        self.clock = 0.; self.started = self.touched = self.uncertain = self.restoring = False
        self.events = []; self.counts = {}; self.failures = set(failures)
        self.binding = w.BINDING; self.power = 100; self.full = full; self.accepts500 = accepts500
        self.bad_sample = {}; self.bad_before = {}; self.child = None
        self.env_changed = False; self.expire_at = None
        self.ever500 = False
        self.applied_failures=set();self.gap_each_500=0
        self.final_fault=False

    def edge(self, name):
        self.events.append(name); self.counts[name] = self.counts.get(name, 0) + 1
        key = name + ':' + str(self.counts[name])
        if 'unknown:' + key in self.failures:
            self.uncertain = True
            raise w.r6.MutationUncertain(key)
        if key in self.failures:
            raise RuntimeError('known completed failure ' + key)

    def begin(self, cfg):
        self.edge('begin'); assert cfg['transaction'] == w.TX
        self.started = True

    def preflight(self):
        self.edge('preflight')
        row = self.snapshot(); row['sample'].update(self.bad_before)
        return row

    def event(self, name, **fields):
        if name != 'sample': self.edge('event:' + name)

    def now(self): return self.clock
    def pause(self, seconds): self.clock += seconds

    def gadget_state(self):
        self.edge('gadget')
        return {'binding': self.binding, 'power_ma': self.power}

    def snapshot(self):
        self.edge('snapshot')
        if self.power == 500:self.clock+=self.gap_each_500
        allowed = self.power == 100 or self.accepts500
        current = self.power * 1000 if allowed else 0
        s = copy.deepcopy(sample_fixture)
        s.update(budget_ua=current, age_ms=50)
        if self.full:
            s.update(logical_full=1, full_holding=1, hold_requested=1, full_cause=1,
                     desired_enable=0, session_seconds=0)
        if not allowed:
            s.update(source_inhibit=1, desired_enable=0, error=-61)
        if self.power == 500 or self.ever500: s.update(self.bad_sample)
        if self.final_fault and self.counts.get('environment',0)>=2:s['latched']=1
        return {'sample': s,
                'limits': {'native_ua': current, 'input_ua': current if allowed else 100000,
                           'charge_ua': 250000, 'cv_uv': 4362500},
                'registers': {'00': current // 50000 if allowed else 2, '0f': current // 50000 if allowed else 2,
                              '02': 5, '04': 104, '08': (0 if self.full else 16) if allowed else 8},
                'state': {'boot_id': 'same-boot', 'release': w.r6.RELEASE, 'taint': '0',
                          'camera_pm': {'icp': 'suspended'}, 'm2m': 'idle', 'services': ['same-four-pids']},
                'notes': {'samurai-usb-input': 'usb-note', 'samurai-gauge-protection': 'protection-note'},
                'openrc_started': True, 'udc': 'configured' if allowed else 'addressed',
                'source': {'online': '1', 'usb_type': '[SDP]', 'current_max': str(current), 'input_current_limit': str(current)}}

    def write(self, field, value, stage, deadline):
        assert not self.uncertain
        if self.expire_at is not None and self.clock >= self.expire_at and not self.restoring:
            raise RuntimeError('expired forward lease')
        self.touched = True
        self.edge('write:' + stage)
        if field == 'UDC': self.binding = value.strip()
        else:
            self.power = int(value)
            self.ever500 |= self.power == 500
        if stage in self.applied_failures:raise RuntimeError('completed write reported failure after effect '+stage)

    def network(self, deadline): self.edge('network:' + str(self.power))
    def environment(self):
        self.edge('environment')
        return {'camera': 'same', 'counts': 1 if self.env_changed and self.clock else 0}
    def finish(self, result): self.result = copy.deepcopy(result)
    def close(self): self.closed = True


cases = []
def run(name, fake=None):
    f = fake or Fake()
    r = w.transaction(config, f)
    assert f.closed and r == f.result
    cases.append({'name': name, 'passed': True, 'native500': r['native500_accepted'],
                  'restored100': r['restore100_verified'], 'unknown': r['mutating_state_unknown']})
    return r, f


r, f = run('managed-accept500-always-restore100')
assert r['passed'] and r['diagnostic_completed'] and f.power == 100 and f.binding == w.BINDING
assert [e for e in f.events if e.startswith('write:')] == [
    'write:500:unbind','write:500:power','write:500:bind','write:100:unbind','write:100:power','write:100:bind']
r, f = run('exact-Full-accept500-and-restore100', Fake(full=True))
assert r['passed'] and r['accepted500_state'] == r['restored_state'] == 'full_holding'
r, f = run('host-rejects500-capture-completes-after100', Fake(accepts500=False))
assert not r['passed'] and r['diagnostic_completed'] and r['restore100_verified'] and not r['native500_accepted']

for field, value in [('latched',1),('cycle_timeout',1),('fault',1),('error',-5),('gauge_charge_stop',1),('thermal_inhibit',1)]:
    fake=Fake();fake.bad_before[field]=value
    r,f=run('preflight-reject-'+field,fake)
    assert not r['passed'] and not f.touched and not any(x.startswith('write:') for x in f.events)

for stage in ['500:unbind','500:power','500:bind']:
    r,f=run('known-failure-'+stage,Fake(['write:'+stage+':1']))
    assert r['primary_error'] and r['restore100_verified'] and r['recovery_error'] is None
    assert f.power == 100 and f.binding == w.BINDING
for stage in ['500:unbind','500:power','500:bind']:
    fake=Fake();fake.applied_failures.add(stage)
    r,f=run('known-failure-after-actual-effect-'+stage,fake)
    assert r['primary_error'] and r['restore100_verified'] and f.power==100
for stage in ['100:unbind','100:power','100:bind']:
    r,f=run('restore-failure-'+stage,Fake(['write:'+stage+':1']))
    assert r['native500_accepted'] and r['recovery_error'] and not r['restore100_verified'] and not r['passed']
    assert f.counts['write:'+stage] == 1  # never silently repeat a failed restore

for stage in ['500:unbind','500:power','500:bind','100:unbind','100:power','100:bind']:
    r,f=run('pending-sysfs-no-following-mutation-'+stage,Fake(['unknown:write:'+stage+':1']))
    assert not r['terminal'] and r['mutating_state_unknown'] and r['recovery_error']
    last=f.events.index('write:'+stage)
    assert not any(x.startswith(('write:','network:')) for x in f.events[last+1:])

r,f=run('known-reaped-network-timeout-restores100',Fake(['network:500:1']))
assert r['primary_error'] and r['restore100_verified'] and f.counts['network:100'] == 1
r,f=run('unknown-network-child-no-restore-race',Fake(['unknown:network:500:1']))
assert r['mutating_state_unknown'] and not any(x.startswith('write:100') for x in f.events)
r,f=run('restore-network-error-not-falsely-verified',Fake(['network:100:1']))
assert r['recovery_error'] and not r['restore100_verified'] and r['final_gadget'] == {'binding':w.BINDING,'power_ma':100}

for field,value in [('latched',1),('cycle_timeout',1),('fault',1)]:
    fake=Fake();fake.bad_sample[field]=value
    r,f=run('fault-during500-restores-descriptor-no-AUTO-'+field,fake)
    assert r['primary_error'] and not r['restore100_verified'] and r['descriptor100_bound']
    assert r['final_observation']['sample'][field] == value
    assert not any('start' == e or 'auto' == e for e in f.events)
fake=Fake();fake.env_changed=True
r,f=run('environment-count-change-not-claimed-clean',fake)
assert r['recovery_error'] and not r['diagnostic_completed']
fake=Fake(accepts500=False);fake.expire_at=10
r,f=run('expired-forward-but-original100-cleanup-continues',fake)
assert r['restore100_verified'] and f.clock > 10
fake=Fake();fake.gap_each_500=5
r,f=run('healthy-samples-with-five-second-gaps-not-continuous-proof',fake)
assert not r['native500_accepted'] and r['restore100_verified']
fake=Fake();fake.final_fault=True
r,f=run('final-fresh-fault-cannot-pass-after-earlier-stable100',fake)
assert r['final_error'] and not r['passed'] and not r['restore100_verified'] and r['descriptor100_bound']

# Exercise concrete read/write/network boundaries without accessing sysfs/ip.
with tempfile.TemporaryDirectory(prefix='usb500-concrete-') as temp:
    root=Path(temp)
    mapped=lambda *parts: root / str(Path(*parts)).lstrip('/')
    cfg={'identity':{'boot_id':'test-boot'},'window_token':'token','host_trigger_nonce':'a'*48}
    lease={'transaction':w.TX,'owner':'charging','camera_released':True,'bluetooth_released':True,
           'exclusive':True,'token':'token','host_trigger_nonce':'a'*48,'boot_id':'test-boot','expires_boottime_s':90}
    for p in [w.WINDOW,w.r6.GUARD,'/proc/sys/kernel/random/boot_id']:
        file=mapped(p);file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(json.dumps(lease) if p==w.WINDOW else 'test-boot\n');file.chmod(0o600)
    d=w.Diagnostic(temp);d.read_owned=lambda p:(mapped(p).read_bytes(),0o600)
    d.touched=True;d.restoring=True;d.lock=123
    with patch.object(w,'Path',mapped),patch.object(w.time,'clock_gettime',return_value=100):
        try:d.check_window(cfg);raise AssertionError('expired forward accepted')
        except RuntimeError:pass
        cases.append({'name':'actual-forward-expired-lease-refused','passed':True})
        d.check_window(cfg,cleanup=True)
        cases.append({'name':'actual-original-100-cleanup-allows-expired-lease','passed':True})
        for key,value in [('token','other'),('owner','camera'),('boot_id','other-boot')]:
            mapped(w.WINDOW).write_text(json.dumps(dict(lease,**{key:value})))
            rejected=False
            try:d.check_window(cfg,cleanup=True)
            except RuntimeError:rejected=True
            assert rejected
            cases.append({'name':'actual-expired-cleanup-still-refuses-'+key,'passed':True})
        mapped(w.WINDOW).write_text(json.dumps(lease))
        mapped('/proc/sys/kernel/random/boot_id').write_text('other-boot\n')
        try:d.check_window(cfg,cleanup=True);raise AssertionError('cleanup on another real boot accepted')
        except RuntimeError:pass
        mapped('/proc/sys/kernel/random/boot_id').write_text('test-boot\n')
        cases.append({'name':'actual-cleanup-refuses-changed-real-boot-not-only-lease-field','passed':True})
        d.lock=None
        try:d.check_window(cfg,cleanup=True);raise AssertionError('cleanup without original lock accepted')
        except RuntimeError:pass
        cases.append({'name':'actual-cleanup-requires-original-service-lock','passed':True})

    for name,value in [('UDC',w.BINDING),('configs/c.1/MaxPower','100')]:
        file=mapped(w.GADGET,name);file.parent.mkdir(parents=True,exist_ok=True);file.write_text(value)
    d=w.Diagnostic(temp)
    with patch.object(w,'Path',mapped):
        assert d.gadget_state()=={'binding':w.BINDING,'power_ma':100}
        mapped(w.GADGET,'configs/c.1/MaxPower').write_text('900')
        try:d.gadget_state();raise AssertionError('unexpected sysfs accepted')
        except w.r6.MutationUncertain:pass
        assert d.uncertain
        with patch.object(w.subprocess,'Popen') as popen:
            try:d.write('MaxPower','100\n','100:power',d.now()+10);raise AssertionError('wrote after unknown readback')
            except RuntimeError:pass
            assert not popen.called
    cases.append({'name':'actual-unknown-sysfs-readback-blocks-next-mutation','passed':True})

    d=w.Diagnostic(temp);d.started=True;d.out=root;d.config=cfg;d.restoring=True
    with patch.object(w.os,'fsync',side_effect=OSError('injected journal fsync failure')):
        d.event('restore100-start')  # failed journal may not prevent safe100
        assert d.journal_errors
        d.restoring=False
        try:d.event('forward500-before');raise AssertionError('unjournaled forward allowed')
        except OSError:pass
    cases.append({'name':'actual-journal-failure-refuses-forward-but-does-not-block100-cleanup','passed':True})

    file=mapped(w.GADGET,'functions/ncm.usb0/ifname');file.parent.mkdir(parents=True,exist_ok=True);file.write_text('usb0')
    for present in [True,False]:
        d=w.Diagnostic(temp);calls=[]
        def net(args,deadline):
            calls.append(args)
            return json.dumps([{'addr_info':[{'local':'169.254.42.1','prefixlen':16}] if present else []}]) if '-j' in args else ''
        d.net_command=net
        with patch.object(w,'Path',mapped):d.network(d.now()+10)
        assert calls[0]==['ip','link','set','usb0','up'] and len(calls)==(2 if present else 3)
        if not present:assert calls[-1]==['ip','addr','add','169.254.42.1/16','dev','usb0']
        cases.append({'name':'actual-original-network-order-'+('existing-address' if present else 'restore-missing-address'),'passed':True})

class Pending:
    pid=987;returncode=None
    def __init__(self,reaped=False):self.calls=0;self.reaped=reaped;self.killed=False
    def communicate(self,timeout):
        self.calls+=1
        if self.reaped and self.calls>1:self.returncode=-9;return ('','')
        raise subprocess.TimeoutExpired('fixed-operation',timeout)
    def kill(self):self.killed=True

for reaped in [False,True]:
    d=w.Diagnostic('/not-used');d.event=lambda *a,**k:None
    child=Pending(reaped)
    with patch.object(w.subprocess,'Popen',return_value=child):
        try:d.net_command(['ip','link','set','usb0','up'],d.now()+10);raise AssertionError('network timeout accepted')
        except RuntimeError:pass
        assert child.killed and d.uncertain == (not reaped)
    cases.append({'name':'actual-network-timeout-'+('reaped-known' if reaped else 'unreaped-unknown'),'passed':True})

d=w.Diagnostic('/not-used');d.started=True;d.config=cfg;d.event=lambda *a,**k:None;d.check_window=lambda *a,**k:None
child=Pending()
with patch.object(w.subprocess,'Popen',return_value=child) as popen:
    try:d.write('MaxPower','500\n','500:power',d.now()+10);raise AssertionError('sysfs timeout accepted')
    except w.r6.MutationUncertain:pass
    assert d.touched and d.uncertain and not child.killed
    try:d.write('MaxPower','100\n','100:power',d.now()+10);raise AssertionError('follow-up write raced unknown')
    except RuntimeError:pass
    assert popen.call_count==1
cases.append({'name':'actual-sysfs-timeout-retains-pid-without-kill-or-followup-write','passed':True})
d=w.Diagnostic('/not-used');d.restoring=True;d.check_window=lambda *a,**k:None
with patch.object(w.subprocess,'Popen') as popen:
    try:d.write('MaxPower','500\n','500:power',d.now()+10);raise AssertionError('cleanup wrote500')
    except RuntimeError:pass
    assert not popen.called
cases.append({'name':'actual-expired-cleanup-cannot-authorize-any-forward500-write','passed':True})
class Completed:
    pid=321;returncode=0
    def communicate(self,timeout):assert timeout==3;return ('','')
d=w.Diagnostic('/not-used');d.restoring=True;d.started=True;d.event=lambda *a,**k:None;d.check_window=lambda *a,**k:None
d.now=lambda:100
with patch.object(w.subprocess,'Popen',return_value=Completed()) as popen:
    d.write('MaxPower','100\n','100:power',50)
    assert popen.call_count==1 and popen.call_args.args[0][-1]=='100\n'
    d.restoring=False
    try:d.write('MaxPower','500\n','500:power',50);raise AssertionError('expired forward deadline accepted')
    except RuntimeError:pass
    assert popen.call_count==1
cases.append({'name':'actual-elapsed-observation-deadline-still-allows-only-safety100-write','passed':True})

# Audit the actual old closure body rather than inventing its claimed order.
old_source=(MAIN/'usb-reenumerate.py').read_text()
tree=ast.parse(old_source)
old_config=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='configure')
old_body=ast.get_source_segment(old_source,old_config)
assert old_body.index("udc.write_text('\\n')") < old_body.index('power.write_text') < old_body.index('time.sleep(2)') < old_body.index("udc.write_text(binding") < old_body.index('network()')
cases.append({'name':'actual-old-configure-order-audited-and-preserved-with-readback-guards','passed':True})
for file,sha in [('r6-base.py',w.BASE_SHA),('health.py',w.HEALTH_SHA)]:assert w.r6.sha((HERE/file).read_bytes())==sha
tested={name:w.r6.sha((HERE/name).read_bytes()) for name in ['worker.py','test-worker.py','r6-base.py','health.py']}
result={'passed':True,'cases':len(cases),'sequences':cases,'tested_files':tested,
        'actual_r6_sample_receipt_sha256':w.r6.sha((MAIN/'r6-update-result.json').read_bytes()),
        'audited_old_worker_sha256':w.r6.sha((MAIN/'usb-reenumerate.py').read_bytes()),
        'audited_old_configure_sha256':w.r6.sha(old_body.encode()),
        'phone_accessed':False,'network_accessed':False,'sdk_accessed':False,'trial_executed':False,
        'scope':'actual transaction/configure/stability and frozen gates, concrete sysfs/network/lease boundaries with only fake IO/processes'}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(cases),'tested_files':tested},indent=2))
