"""Only new stage-aware gates. No old suite, OS/device action or runtime request."""
from pathlib import Path, PurePosixPath
import ast
import base64
import copy
import hashlib
import json
import re
import stat
import subprocess
import sys
import types
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
cases = []


def load_functions():
    source = (HERE / 'common.py').read_text()
    tree = ast.parse(source)
    ns = dict(Path=PurePosixPath, ROOT=PurePosixPath('/root/charging-management-20261023'),
              base64=base64, hashlib=hashlib, json=json, re=re, stat=stat)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ns[target.id] = value
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(HERE / 'common.py'), 'exec'), ns)
    return ns


def encoded(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


def fixture(ns):
    # These are explicitly synthetic in-memory facts, not current identity or
    # future runtime material. The tiny real frozen payload binds its hash.
    boot = '00000000-0000-4000-8000-000000000001'
    meta = copy.deepcopy(ns['FIXED'])
    meta.update(transaction_id='usb-irq-protection-activate-fixture-00000001', token='9' * 48,
                boot_id=boot, soc_serial_sha256='1' * 64, compatible_sha256=sha(b'realme,samurai\0'),
                rootfs_release_sha256='3' * 64)
    identity = dict(boot_id=boot, version=ns['VERSION'], serial_sha256=meta['soc_serial_sha256'],
                    compatible_sha256=meta['compatible_sha256'], rootfs_sha256=meta['rootfs_release_sha256'])
    before = dict(boot_id=boot, uname=dict(version=ns['VERSION'], release=ns['RELEASE'], machine='aarch64'),
                  taint='0', serial_sha256='1' * 64, rootfs=dict(sha256='3' * 64),
                  compatible_b64=base64.b64encode(b'realme,samurai\0').decode())
    proof = dict(postboot_raw_sha256='4' * 64,
                 result=dict(passed=True, read_only=True, hardware_writes=0, errors=[],
                             checks={name: dict(ready=True) for name in ns['CHECKS']}),
                 raw=dict(identity_before=before, identity_after=copy.deepcopy(before),
                          boot_partition=dict(sha256=ns['BOOT'], bytes=100663296),
                          logdump_partition=dict(sha256=ns['LOGDUMP'], bytes=67108864),
                          manifest=dict(sha256=ns['OLD']), manifest_text='{"adapter_revision":"r8"}',
                          charging_modules={name: dict(loaded_note_sha256=digest) for name, digest in ns['OLD_NOTES'].items()}))
    meta['adoption'] = dict(transaction_id='image502-fixture-00000001',
                            guard_path='/var/lib/samurai/image502-fixture-00000001-adopted/boot-id-private.txt',
                            guard_sha256=sha((boot + '\n').encode()), postboot_raw_sha256='4' * 64,
                            fresh_validation_sha256=sha(encoded(proof)))
    stage = 'usb-irq-protection-stage-fixture-00000001'
    payload = Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/usb-irq-protection-payload.tar.gz').read_bytes()
    assert sha(payload) == ns['PAYLOAD']
    request = dict(schema='samurai-usb-irq-protection-stage-request-v1', transaction_id=stage,
                   cohort_delivery_sha256=ns['FIXED']['cohort_delivery_sha256'], payload_sha256=ns['PAYLOAD'],
                   payload_base64=base64.b64encode(payload).decode(), worker_sha256=ns['STAGE_WORKER'],
                   identity=identity, adoption={k: meta['adoption'][k] for k in
                    ['transaction_id', 'guard_path', 'guard_sha256', 'postboot_raw_sha256']}, lease_token='5' * 48)
    request_sha = sha(encoded(request))
    paths = ns['stage_paths'](stage)
    root = ns['ROOT'] / stage
    wargv = ['python3', '-B', str(root / 'stage-worker.py'), '--execute-stage']
    sargv = ['python3', '-B', str(root / 'stage-supervisor.py'), '--execute-supervisor']
    w = dict(transaction_id=stage, boot_id=boot, pid=101, start_ticks=12345, argv=wargv, worker_sha256=ns['STAGE_WORKER'])
    s = dict(transaction_id=stage, boot_id=boot, pid=100, start_ticks=12344, argv=sargv, request_sha256=request_sha)
    result = dict(schema='samurai-usb-irq-protection-stage-result-v1', transaction_id=stage,
        cohort_delivery_sha256=ns['FIXED']['cohort_delivery_sha256'], payload_sha256=ns['PAYLOAD'],
        terminal=True, staged=True, phase='staged', status='staged/runtime_pending', runtime_pending=True,
        disk_state='all_new_fsynced', stop_verified=True, unknown_write_state=False,
        primary_error=None, stop_error=None, activation_attempted=False, new_module_loaded=False,
        capture_issued=False, automatic_rollback_or_replay=False, source_boot_id=boot,
        source_version=ns['VERSION'], source_guard_path=meta['adoption']['guard_path'],
        old_manifest_sha256=ns['OLD'], new_manifest_sha256=ns['FIXED']['charging_manifest_sha256'],
        old_resident_notes=copy.deepcopy(ns['OLD_NOTES']), resident_notes_expected=copy.deepcopy(ns['OLD_NOTES']),
        adoption_fresh_validation_sha256=meta['adoption']['fresh_validation_sha256'],
        final_files={name: dict(sha256=digest, new_sha256=digest, old_sha256=ns['OLD_FILES'][name],
                               mode='0o600', classification='new') for name, digest in ns['FIXED']['new_disk_files'].items()},
        temporary_files={name: dict(state='absent') for name in ns['FIXED']['new_disk_files']})
    records = dict(request=request, result=result, worker_process=w, supervisor_process=s,
                   worker_launch=dict(w, request_sha256=request_sha, supervisor_pid=s['pid']),
                   worker_terminal=dict(transaction_id=stage, boot_id=boot, pid=w['pid'], argv=wargv,
                    request_sha256=request_sha, supervisor_pid=s['pid'], terminal=True, returncode=0),
                   supervisor_launch=copy.deepcopy(s),
                   supervisor_terminal=dict(s, terminal=True, returncode=0, worker_pid=w['pid'], worker_returncode=0),
                   before=sample(ns), stopped=sample(ns), after=sample(ns),
                   adoption_proof=dict(actual_fresh_validation_sha256=meta['adoption']['fresh_validation_sha256'],
                    postboot_raw_sha256=meta['adoption']['postboot_raw_sha256'], guard_sha256=meta['adoption']['guard_sha256']))
    raws = {name: encoded(value) for name, value in records.items()}
    raws['worker_source'] = (REF / 'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py').read_bytes()
    raws['supervisor_source'] = (REF / 'charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/stage-supervisor.py').read_bytes()
    meta['stage'] = dict(transaction_id=stage, request_sha256=request_sha, result_sha256=sha(raws['result']),
                         host_binding_sha256='6' * 64, worker_sha256=ns['STAGE_WORKER'],
                         supervisor_sha256=ns['STAGE_SUPERVISOR'],
                         evidence={name: dict(path=paths[name], sha256=sha(raw)) for name, raw in raws.items()})
    claim = dict(transaction_id=stage, boot_id=boot, request_sha256=request_sha, request_count=1,
                 argv=wargv, supervisor_argv=sargv, supervisor_sha256=ns['STAGE_SUPERVISOR'])
    processes = dict(worker=dict(state='absent', pid=w['pid']), supervisor=dict(state='zombie', pid=s['pid'], start_ticks=s['start_ticks']))
    return meta, records, processes, claim, raws, proof


def sample(ns, cdp=False, full=False):
    current, budget = (900000, 1500000) if cdp else (500000, 500000)
    s = {k: 0 for k in ['shadow', 'error', 'stop_error', 'latched', 'fault', 'source_inhibit',
        'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop', 'flags', 'logical_full', 'hold_requested',
        'full_holding', 'full_cause', 'desired_enable']}
    s.update(valid=1, protection_ok=1, online=1, age_ms=5, session_seconds=10, cell1_uv=4300000,
             cell2_uv=4300000, pack_uv=8600000, temp_decic=265, thermal_band=4, budget_ua=budget)
    if full:
        s.update(logical_full=1, full_cause=3, session_seconds=0)
    return dict(read_start=99.5, read_end=99.8, sample=s,
        state=dict(registers={'00': current // 50000, '01': 0, '02': 5, '03': 0, '04': 0x68,
                             '05': 0, '07': 0, '08': 8, '09': 0, '0f': current // 50000, '13': 2},
                   taint='0', driver='samurai-mp2650', camera_pm={str(k): 'suspended' for k in range(4)},
                   m2m=json.dumps(dict(users=0, orphans=0, jobs=0, first_error=0, running=False, fatal=False, pinned=False)),
                   services=[dict(comm=c, uid=10000, pid=i + 1) for i, c in enumerate(['phoc', 'phosh', 'pipewire', 'wireplumber'])]),
        notes=copy.deepcopy(ns['OLD_NOTES']), openrc_started=True, protection_health='Good',
        protection=dict(id=0x2719, error=0, safety=0, pf=0, operation=0x300, manufacturing=0x18),
        source=dict(online='1', usb_type='[CDP]' if cdp else '[SDP]', current_max=str(budget), input_current_limit='500000'),
        limits=dict(input_ua=current, charge_ua=250000, cv_pack_uv=8725000), charge_behaviour='auto [inhibit-charge]')


class Delta(unittest.TestCase):
    def setUp(self):
        self.ns = load_functions()
        self.meta, self.records, self.processes, self.claim, self.raws, self.proof = fixture(self.ns)

    def reject(self, function):
        with self.assertRaises((ValueError, AssertionError, KeyError)):
            function()

    def validate(self):
        return self.ns['validate_stage_records'](self.meta, self.records, self.processes, self.claim)

    def test_original_stage_new_disk_old_live(self):
        self.assertEqual(self.validate(), self.records['request'])
        self.records['worker_launch']['start_ticks'] = None
        self.records['supervisor_launch']['start_ticks'] = None
        self.validate()  # Fast terminal launch may lack ticks, own receipts may not.

    def test_failed_partial_unknown_stage(self):
        clean = copy.deepcopy(self.records)
        mutations = [lambda r: r['result'].update(staged=False),
                     lambda r: r['result'].update(unknown_write_state=True),
                     lambda r: r['result'].update(receipt_error={'error': 'injected'}),
                     lambda r: r['result']['final_files'][next(iter(self.ns['OLD_FILES']))].update(classification='old'),
                     lambda r: r['result']['temporary_files'][next(iter(self.ns['OLD_FILES']))].update(state='unknown'),
                     lambda r: r['result'].update(new_module_loaded=True)]
        for mutation in mutations:
            self.records = copy.deepcopy(clean); mutation(self.records)
            self.reject(self.validate)

    def test_old_boot_and_request_rebinding(self):
        clean = copy.deepcopy(self.records)
        for key, value in [('source_boot_id', '00000000-0000-4000-8000-000000000002'), ('source_version', '#501')]:
            self.records = copy.deepcopy(clean); self.records['result'][key] = value
            self.reject(self.validate)
        self.records = copy.deepcopy(clean); self.records['request']['payload_base64'] = base64.b64encode(b'wrong').decode()
        self.reject(self.validate)
        self.records = copy.deepcopy(clean); self.records['request']['identity']['version'] = '#503'
        self.reject(self.validate)

    def test_original_supervised_terminal_only(self):
        clean = copy.deepcopy(self.records)
        for name, key, value in [('worker_terminal', 'returncode', 255), ('supervisor_terminal', 'worker_returncode', 1),
                                 ('worker_terminal', 'terminal', False), ('worker_launch', 'supervisor_pid', 999),
                                 ('worker_terminal', 'request_sha256', 'f' * 64), ('worker_process', 'start_ticks', None),
                                 ('supervisor_terminal', 'argv', ['python3', 'different-worker.py'])]:
            self.records = copy.deepcopy(clean); self.records[name][key] = value
            self.reject(self.validate)
        self.records = copy.deepcopy(clean); self.claim['request_count'] = 2
        self.reject(self.validate)

    def test_current_process_unknown_is_not_terminal(self):
        for role in ['worker', 'supervisor']:
            for state in ['alive', 'unknown', 'pid_reused']:
                current = copy.deepcopy(self.processes)
                current[role]['state'] = state
                self.reject(lambda: self.ns['validate_stage_records'](self.meta, self.records, current, self.claim))
        self.processes['supervisor']['start_ticks'] += 1
        self.reject(self.validate)

    def test_evidence_exact_remote_projection(self):
        paths = self.ns['stage_paths'](self.meta['stage']['transaction_id'])
        self.assertEqual(set(paths), set(self.raws))
        self.assertTrue(paths['request'].endswith('/request-private.json'))
        self.assertNotIn('/device-stage/', paths['request'])
        clean = copy.deepcopy(self.meta)
        self.meta['stage']['evidence']['worker_terminal']['path'] = 'E:/host-copy.json'
        self.reject(self.validate)
        self.meta = copy.deepcopy(clean); self.meta['stage']['evidence']['worker_source']['sha256'] = '0' * 64
        self.reject(self.validate)
        self.meta = copy.deepcopy(clean); self.meta['stage']['evidence']['host_binding'] = dict(path='/fake', sha256='0' * 64)
        self.reject(self.validate)

    def test_read_stage_hashes_originals_and_adoption(self):
        raw_by_path = {self.meta['stage']['evidence'][k]['path']: v for k, v in self.raws.items()}
        root = self.ns['ROOT'] / self.meta['stage']['transaction_id']
        raw_by_path[str(root / 'launch-claim-private.json')] = encoded(self.claim)
        proof_path = str(PurePosixPath(self.meta['adoption']['guard_path']).parent / 'fresh-validation-private.json')
        raw_by_path[proof_path] = encoded(self.proof)
        self.ns['owned_directory'] = lambda p: PurePosixPath(p)
        self.ns['raw_owned'] = lambda p: raw_by_path[str(p)]
        self.ns['process_observation'] = lambda receipt: dict(state='absent', pid=receipt['pid'])
        self.assertEqual(self.ns['read_stage'](self.meta), self.records)
        before_path = self.meta['stage']['evidence']['before']['path']
        raw_by_path[before_path] += b' '
        self.reject(lambda: self.ns['read_stage'](self.meta))
        raw_by_path[before_path] = self.raws['before']
        bad = copy.deepcopy(self.proof); bad['raw']['boot_partition']['sha256'] = 'f' * 64
        raw_by_path[proof_path] = encoded(bad)
        self.meta['adoption']['fresh_validation_sha256'] = sha(encoded(bad))
        self.records['adoption_proof']['actual_fresh_validation_sha256'] = sha(encoded(bad))
        self.records['result']['adoption_fresh_validation_sha256'] = sha(encoded(bad))
        for name in ['adoption_proof', 'result']:
            raw_by_path[self.meta['stage']['evidence'][name]['path']] = encoded(self.records[name])
            self.meta['stage']['evidence'][name]['sha256'] = sha(encoded(self.records[name]))
        self.meta['stage']['result_sha256'] = self.meta['stage']['evidence']['result']['sha256']
        self.reject(lambda: self.ns['read_stage'](self.meta))

    def test_fresh_inhibit_sdp_cdp_and_retained_full(self):
        for cdp in [False, True]:
            for full in [False, True]:
                data = sample(self.ns, cdp, full)
                answer = self.ns['staged_health'](data, 100)
                self.assertTrue(answer['stage_INHIBIT_reverified'])
                self.assertEqual(answer['hardware_input_ua'], 900000 if cdp else 500000)
                self.ns['environment'](data)

    def test_stage_success_does_not_override_current_changes(self):
        mutations = [lambda d: d['sample'].update(latched=1), lambda d: d['sample'].update(thermal_inhibit=1),
                     lambda d: d.update(read_end=98.9), lambda d: d['state']['registers'].update({'08': 0x10}),
                     lambda d: d['source'].update(usb_type='[UNKNOWN]'), lambda d: d['source'].update(current_max='100000'),
                     lambda d: d['source'].update(input_current_limit='100000'),
                     lambda d: d['notes'].update({'samurai-usb-input': 'f' * 64}),
                     lambda d: d['state']['camera_pm'].update({'0': 'active'}),
                     lambda d: d['state']['registers'].update({'0f': 18}),
                     lambda d: d['sample'].update(logical_full=1, full_cause=3, full_holding=1),
                     lambda d: d['state'].update(taint='512')]
        for mutation in mutations:
            data = sample(self.ns); mutation(data)
            self.reject(lambda: self.ns['staged_health'](data, 100))

    def test_activation_is_new_and_fixed_to_502_boot_only(self):
        path = self.ns['ROOT'] / self.meta['transaction_id'] / 'guard-private.json'
        self.ns['validate_meta_shape'](self.meta, path)
        for key, value in [('transaction_id', 'image502-notify-live-001'), ('kernel_version', '#503'),
                           ('partitions', ['boot', 'logdump']), ('unchanged_logdump_sha256', 'f' * 64)]:
            bad = copy.deepcopy(self.meta); bad[key] = value
            self.reject(lambda: self.ns['validate_meta_shape'](bad, path))

    def test_actual_proc_parser_retains_instance(self):
        class Proc:
            text = '101 (worker with spaces) ' + ' '.join(['Z'] + ['0'] * 18 + ['12345'] + ['0'] * 5)
            error = None
            def __init__(self, *parts): pass
            def read_text(self):
                if self.error: raise self.error
                return self.text
        self.ns['Path'] = Proc
        r = self.records['worker_process']
        self.assertEqual(self.ns['process_observation'](r)['state'], 'zombie')
        Proc.text = Proc.text.replace('12345', '12346')
        self.assertEqual(self.ns['process_observation'](r)['state'], 'pid_reused')
        Proc.error = PermissionError()
        self.assertEqual(self.ns['process_observation'](r)['state'], 'unknown')
        Proc.error = FileNotFoundError()
        self.assertEqual(self.ns['process_observation'](r)['state'], 'absent')

    def test_service_flock_failure_closes_only_own_fd(self):
        events = []
        fake_os = types.SimpleNamespace(O_RDWR=2, O_NOFOLLOW=0x20000,
            open=lambda path, flags: (events.append(('open', path, flags)) or 71),
            fstat=lambda fd: types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o600),
            close=lambda fd: events.append(('close', fd)))
        def lock(fd, mode):
            events.append(('lock', fd, mode)); raise BlockingIOError('busy original owner')
        self.ns.update(os=fake_os, fcntl=types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=lock))
        with self.assertRaises(BlockingIOError): self.ns['acquire_service_lock']()
        self.assertEqual(events[-1], ('close', 71))
        self.assertIsNone(self.ns['_SERVICE_FD'])
        events.clear(); self.ns['fcntl'].flock = lambda fd, mode: events.append(('lock', fd, mode))
        self.ns['acquire_service_lock']()
        self.assertEqual(self.ns['_SERVICE_FD'], 71)
        self.reject(self.ns['acquire_service_lock'])
        self.assertEqual(len(events), 2)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Delta)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    defaults = []
    for worker in ['eud-quiesce.py', 'eud-restart.py']:
        for flags, expected in [([], 0), (['-O'], 1)]:
            command = [sys.executable, '-B', *flags, str(HERE / worker), '--check-local']
            child = subprocess.run(command, capture_output=True, text=True, timeout=10)
            assert child.returncode == expected, child.stderr
            if not flags:
                assert json.loads(child.stdout) == dict(source_only=True, device_accessed=False, request_generated=False)
            else:
                assert 'optimized interpreter is unsupported' in child.stderr
            defaults.append(dict(worker=worker, optimized=bool(flags), returncode=child.returncode))
    receipt = dict(passed=result.wasSuccessful(), scope='new stage-aware actual functions only; all device/OS boundaries fake',
        methods=result.testsRun, failures=len(result.failures), errors=len(result.errors), default_checks=defaults,
        fixture_identity='synthetic in-memory only', runtime_request_generated=False, device_accessed=False,
        old_suites_rerun=False, tested_files={name: sha((HERE / name).read_bytes()) for name in
         ['common-body.py', 'common.py', 'eud-quiesce.py', 'eud-restart.py', 'prepare.py', 'prepare-contract.json', 'source-reuse.json', 'test-delta.py']})
    (HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    if not result.wasSuccessful(): raise SystemExit(1)
    print(json.dumps(dict(passed=True, methods=result.testsRun, default_checks=len(defaults))))
