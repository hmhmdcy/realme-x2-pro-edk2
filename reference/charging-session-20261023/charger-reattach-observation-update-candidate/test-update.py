"""New composition boundaries only. Hardware/file/process edges are models, not phone evidence."""
from pathlib import Path
import base64, copy, hashlib, importlib.util, json, os, tempfile, time, tarfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
spec = importlib.util.spec_from_file_location('worker', HERE / 'stage-worker.py')
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
payload = (PRIVATE / 'charger-reattach-observation-payload-private-01/forward-two-files.tar.gz').read_bytes()
oldraw = (ROOT / 'reference/charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/manifest.json').read_bytes()
oldko = (PRIVATE / 'r8-candidate/samurai-mp2650.ko').read_bytes()
with tarfile.open(PRIVATE / 'r6-candidate/r5-to-r6-payload.tar.gz') as archive:
    service = archive.extractfile(u.SERVICE.lstrip('/')).read()
assert u.sha(service) == u.SERVICE_SHA
observed = json.loads((PRIVATE / 'charger-readonly-before-update-01-private/stdout-private.json').read_bytes())
baseline = {k: int(v, 0) for k, v in (x.split('=') for x in observed['telemetry'].split())}
request = dict(schema='samurai-charger-reattach-update-v1', transaction_id='charger-reattach-update-offline-fixture',
               worker_sha256=u.sha((HERE / 'stage-worker.py').read_bytes()),
               identity=dict(boot_id='11111111-2222-3333-4444-555555555555', version=u.VERSION,
                             serial_sha256='1'*64, compatible_sha256='2'*64, rootfs_sha256='3'*64),
               adoption=dict(transaction_id='usb-irq-protection-activate-fixture0001',
                             guard_path='/var/lib/samurai/usb-irq-protection-activate-fixture0001-adopted/boot-id-private.txt', guard_sha256='4'*64),
               lease_token='5'*48, old_manifest_sha256=u.OLD, new_manifest_sha256=u.NEW,
               payload_sha256=u.PAYLOAD, payload_base64=base64.b64encode(payload).decode())
newfiles, newmeta = u.unpack_request(request)


class Fake(u.Device):
    def __init__(self, full=False, failures=()):
        super().__init__(json.dumps(request).encode())
        self.request = copy.deepcopy(request)
        self.files = {u.KO: (oldko, 0o600), u.MANIFEST: (oldraw, 0o600), u.SERVICE: (service, 0o755)}
        self.loaded = 'old'; self.running = True; self.full = full; self.created = False
        self.failures = set(failures); self.count = {}; self.records = {}; self.carrier_checks = 0
        self.invalid = {}; self.source_changed = False; self.cache_changed = False; self.protection_bad = False
        self.source_kind = 'SDP'; self.budget = 500000; self.input = 500000; self.charge = 250000
        self.closed = False

    def edge(self, event):
        self.events.append(event); self.count[event] = self.count.get(event, 0) + 1
        if event in self.failures:
            self.failures.remove(event)
            if event.startswith('unknown:'):
                self.uncertain = True; raise u.MutationUncertain(event)
            raise RuntimeError('injected:' + event)

    def begin(self, req):
        self.edge('begin'); assert not self.created; self.created = True
        self.check_window(req)

    def open_readonly(self, req): self.edge('readonly'); self.check_window_readonly = False
    def identity(self, req): return dict(req['identity'], guard_sha256=req['adoption']['guard_sha256'])
    def check_window(self, req): self.edge('window')
    def read_owned(self, name): return self.files[name]
    def verify_carriers(self): self.carrier_checks += 1
    def manager(self, digest):
        assert digest == u.SERVICE_SHA
        def command(meta, action):
            self.edge(action)
            if action == 'stop': self.running = False
            else: self.running = True
        return {'_r8_code_sha256': digest, 'command': command}
    def manager_for_stop(self): return self.manager(u.SERVICE_SHA)
    def verify(self, manager):
        meta = json.loads(self.files[u.MANIFEST][0])
        assert u.sha(self.files[u.KO][0]) == meta['installed_files'][u.KO]
        return meta
    def notes_match(self, manager, meta):
        assert self.loaded == ('old' if meta['installed_files'][u.KO] == u.OLD_CHARGER else 'new')
    def module_state(self, name='samurai-mp2650'): return 'live' if name in u.PROVIDERS or self.loaded else 'absent'
    def module_present(self): return self.loaded is not None

    def observe(self, manager):
        self.edge('observe:' + str(self.loaded))
        s = copy.deepcopy(baseline)
        s.update(logical_full=int(self.full), full_holding=int(self.full and self.running), hold_requested=int(self.full and self.running),
                 full_cause=3 if self.full else 0, desired_enable=int(self.running and not self.full), session_seconds=0,
                 budget_ua=self.budget)
        if self.loaded == 'new': s.update(self.invalid)
        lim = dict(native_ua=500000, source_budget_ua=self.budget, input_ua=self.input, charge_ua=self.charge, cv_uv=4362500)
        source = dict(online='1', usb_type='Unknown [' + self.source_kind + '] DCP CDP C', current_max=str(self.budget), input_current_limit='500000')
        if self.source_changed: source['input_current_limit'] = '100000'; lim['native_ua'] = 100000
        bits = 8 if not self.running else (0 if self.full else 0x10)
        state = dict(boot_id=request['identity']['boot_id'], release=u.RELEASE, taint='0', driver='samurai-mp2650',
                     camera_pm={str(i): 'suspended' for i in range(4)},
                     m2m=json.dumps(dict(users=0, orphans=0, jobs=0, first_error=0, running=False, fatal=False, pinned=False)),
                     services=[dict(comm=k, pid=i+20, uid=10000) for i, k in enumerate(('phoc','phosh','pipewire','wireplumber'))])
        r = {'00': self.input//50000, '0f': self.input//50000, '02': self.charge//50000, '04': 104, '08': bits}
        state['registers'] = r
        now = time.clock_gettime(time.CLOCK_BOOTTIME)
        return dict(state=state, sample=s, limits=lim, source=source, registers=r, notes=dict(u.NOTES, **{'samurai-mp2650': u.NEW_NOTE if self.loaded == 'new' else u.NOTES['samurai-mp2650']}),
                    openrc_started=True, read_start=now, read_end=now, protection_health='Good',
                    protection=dict(id=0x2719, error=0, safety=int(self.protection_bad), pf=0, operation=0x300, manufacturing=0x18),
                    identity=self.identity(request), mac_evidence={'sha256': 'changed' if self.cache_changed else observed['mac_cache_sha256'], 'attribute_inode': 19})

    def registers(self): return self.observe(self.manager(u.SERVICE_SHA))['registers']
    def backup(self, files, before): self.edge('backup'); self.before = before; self.saved = copy.deepcopy(files)
    def unload(self):
        self.edge('unload'); self.edge('unknown:unload'); assert not self.running
        self.loaded = None
    def replace(self, name, content, mode):
        self.edge('replace:' + Path(name).name)
        assert name in u.MODES and mode == 0o600 and (self.loaded is None or not self.running)
        self.files[name] = (content, mode)
    def load(self, path):
        self.edge('load'); assert self.loaded is None; self.loaded = 'new' if u.sha(self.files[u.KO][0]) == u.HASHES[u.KO] else 'old'
        self.charge = 1100000; self.running = False
    def cap_inhibited(self, before):
        self.edge('cap'); assert not self.running; self.input = before['limits']['input_ua']; self.charge = 250000
    def log(self, name, data): self.records[name] = copy.deepcopy(data)
    def finish(self, result):
        self.edge('finish'); result['final_files'] = {k: {'sha256': u.sha(self.files[k][0]), 'mode': oct(self.files[k][1])} for k in u.MODES}
        result['installed_new'] = all(result['final_files'][k]['sha256'] == u.HASHES[k] for k in u.MODES)
        self.log('result.json', result)
    def close(self): self.edge('close'); self.closed = True


results = []
def case(name, fn):
    fn(); results.append({'name': name, 'passed': True})
def rejects(fn):
    try: fn()
    except Exception: return
    raise AssertionError('expected rejection')


def schema():
    u.manifest_delta(json.loads(oldraw), newmeta)
    for field, value in [('old_manifest_sha256','0'*64), ('new_manifest_sha256','0'*64), ('schema','old'), ('transaction_id','charging-update-r8')]:
        r = copy.deepcopy(request); r[field] = value; rejects(lambda: u.unpack_request(r))
case('actual-two-file-payload-and-new-request-reject-old-bindings', schema)

def full_preflight():
    f = Fake(full=True); r = u.preflight(request, f, f.request_raw)
    assert r['passed'] and r['healthy_state'] == 'full_holding' and not r['eligible'] and r['reason'] == 'full_state_not_restorable'
    assert not any(x in f.events for x in ('stop','unload','begin','backup')) and f.closed
    f = Fake(full=True); r = u.update(request, f)
    assert not r['passed'] and not any(x in f.events for x in ('stop','unload','backup')) and f.full
case('healthy-Full-is-readonly-accepted-but-update-refused-before-stop', full_preflight)

def managed():
    f = Fake(); p = u.preflight(request, f, f.request_raw); assert p['passed'] and p['eligible'] and not f.created
    f = Fake(); r = u.update(request, f)
    assert r['passed'] and r['installed_new'] and f.count['unload'] == 1 and f.count['load'] == 1
    assert f.events.index('cap') < f.events.index('start') and f.charge == 250000
    assert f.records['before-private.json'] if 'before-private.json' in f.records else f.before
    assert f.records['after-private.json']['mac_evidence'] == f.before['mac_evidence']
case('actual-ordered-managed-SDP500-two-file-transaction-and-cap-before-start', managed)

def sources():
    for kind, budget in [('CDP',1500000),('DCP',1500000),('C',1500000),('C',3000000)]:
        f = Fake(); f.source_kind = kind; f.budget = budget; f.input = 900000
        assert u.update(request, f)['passed']
    for kind, budget in [('Unknown',500000),('SDP',1500000),('CDP',500000)]:
        f = Fake(); f.source_kind = kind; f.budget = budget
        r = u.update(request, f); assert not r['passed'] and 'unload' not in f.events
case('explicit-classified-source-budgets-no-hardcoded-SDP100-or-guessed-permission', sources)

def changes():
    for field in ('source_changed', 'cache_changed', 'protection_bad'):
        class Changed(Fake):
            def cap_inhibited(self, before):
                super().cap_inhibited(before); setattr(self, field, True)
        f = Changed(); r = u.update(request, f)
        assert not r['passed'] and 'start' not in f.events and not f.running
        assert r.get('observed_unsafe_state_preserved_in_live_module') is True
        assert f.loaded == 'new' and f.count['unload'] == 1
case('changed-source-cache-or-protection-preserved-inhibited-without-provider-reload', changes)

def late_full():
    class Late(Fake):
        def manager_command(self, m, meta, action):
            answer = super().manager_command(m, meta, action)
            if action == 'stop': self.full = True
            return answer
    f = Late(); r = u.update(request, f)
    assert not r['passed'] and 'unload' not in f.events and 'start' not in f.events
case('Full-acquired-after-preflight-prevents-unload', late_full)

def rollback():
    f = Fake(failures=('replace:samurai-mp2650.ko',)); r = u.update(request, f)
    assert not r['passed'] and f.loaded == 'old' and f.running
    assert f.files[u.MANIFEST][0] == oldraw and f.files[u.KO][0] == oldko
    assert f.count['unload'] == 1 and f.count['load'] == 1
case('original-exact-two-file-rollback-tail-safe-source-restart', rollback)

def newfault():
    class Fault(Fake):
        def cap_inhibited(self, before):
            super().cap_inhibited(before); self.invalid.update(latched=1, fault=2, error=-5)
    f = Fault(); r = u.update(request, f)
    assert not r['passed'] and f.loaded == 'new' and not f.running and 'start' not in f.events
    assert r['observed_unsafe_state_preserved_in_live_module'] and f.count['unload'] == 1
case('new-fault-keeps-consistent-new-disk-live-module-inhibited-no-fault-amnesty', newfault)

def unknown():
    f = Fake(failures=('unknown:unload',)); r = u.update(request, f)
    assert not r['terminal'] and r['mutating_process_unknown'] and 'load' not in f.events and 'start' not in f.events
    assert not any(isinstance(e,str) and e.startswith('replace:') for e in f.events)
case('unknown-original-mutating-child-no-second-mutation', unknown)

def malformed_full():
    for key, val in [('session_seconds',1),('full_cause',0),('desired_enable',1),('hold_requested',0)]:
        f = Fake(full=True); row = f.observe(f.manager(u.SERVICE_SHA)); row['sample'][key] = val
        rejects(lambda: u.healthy(row))
    f = Fake(); row=f.observe(f.manager(u.SERVICE_SHA)); row['sample']['full_cause']=3
    rejects(lambda: u.healthy(row))
case('exact-Full-and-normal-consistency-gates', malformed_full)

def lease():
    f = Fake(); lease = dict(transaction_id=request['transaction_id'], boot_id=request['identity']['boot_id'], token=request['lease_token'], owner='charging',
                            exclusive=True, camera_released=True, bluetooth_released=True, issued_boottime_s=10, expires_boottime_s=130)
    f.read_owned=lambda _: (json.dumps(lease).encode(),0o600)
    with patch.object(u.time,'clock_gettime',return_value=20):
        u.Device.check_window(f,request)
        lease['expires_boottime_s']=131; rejects(lambda:u.Device.check_window(f,request))
        lease['expires_boottime_s']=20; rejects(lambda:u.Device.check_window(f,request))
        lease['expires_boottime_s']=130; lease['bluetooth_released']=False; rejects(lambda:u.Device.check_window(f,request))
case('actual120-second-lease-fields-expiry-and-coordinated-window', lease)

def lock():
    with tempfile.TemporaryDirectory() as name:
        path=Path(name)/'existing-lock'; path.write_bytes(b''); path.chmod(0o600)
        f=Fake()
        with patch.object(u,'LOCK',str(path)):
            u.Device.lock_existing(f,True); assert path.read_bytes()==b''; os.close(f.lock); f.lock=None
            path.unlink(); rejects(lambda:u.Device.lock_existing(f,True)); assert not path.exists()
case('actual-readonly-preflight-existing-shared-lock-never-creates-missing-lock', lock)

def actual_caps():
    with tempfile.TemporaryDirectory() as name:
        supply=Path(name); f=Fake(); before=f.observe(f.manager(u.SERVICE_SHA)); f.running=False
        r=dict(before['registers'], **{'08':8})
        f.registers=lambda:copy.deepcopy(r)
        original=u.Path
        with patch.object(u,'Path',side_effect=lambda p: supply if p=='/sys/class/power_supply/mp2650-input' else original(p)):
            u.Device.cap_inhibited(f,before)
            assert (supply/'input_current_limit').read_text()=='500000\n'
            assert (supply/'constant_charge_current').read_text()=='250000\n'
            r['08']=0x10
            (supply/'input_current_limit').write_text('unchanged')
            rejects(lambda:u.Device.cap_inhibited(f,before))
            assert (supply/'input_current_limit').read_text()=='unchanged'
            r['08']=8; r['02']=22
            rejects(lambda:u.Device.cap_inhibited(f,before))
case('actual-inhibited-cap-function-safe-fields-readback-and-prewrite-refusal', actual_caps)

def close_failed():
    f=Fake(failures=('close',)); result=u.update(request,f)
    assert not result['passed'] and result.get('close_error') and f.records['result.json']['passed'] is False
case('close-error-published-before-final-result-and-never-passed', close_failed)

out={'schema':'samurai-charger-reattach-update-directed-tests-v1','passed':True,'groups':len(results),'cases':results,
     'tested_files': {p.name:u.sha(p.read_bytes()) for p in [HERE/'stage-worker.py',HERE/'test-update.py']},
     'real_payload_and_old_manifest_used':True,'actual_current_Full_telemetry_used_as_fixture_not_live_identity':True,
     'device_accessed':False,'old_matrices_rerun':False,'hardware_or_deployment_acceptance':False}
(HERE/'test-result.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
