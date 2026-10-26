"""Affected R7 paths only. Fake device/SSH boundaries, actual dispatch/audit."""
from pathlib import Path
import base64
import copy
import importlib.util
import inspect
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


launcher = load(HERE / 'launcher.py', 'r7_launcher')
worker = load(HERE / 'worker.py', 'r7_worker')
audit = load(HERE / 'audit.py', 'r7_audit')
historical = load(HERE.parent / 'icon-capture-candidate/test-candidate.py', 'historical_helpers')


def ready_data(request):
    receipt = {k: request[k] for k in ['transaction', 'token', 'expected_boot', 'manifest_sha256', 'files', 'argv']}
    receipt.update(pid=123, start_ticks=456)
    observations = []
    for tick, boot in [(10, 110.25), (12, 112.45)]:
        status = dict(pid=123, start_ticks=456, active=True, terminal=False, phase='ready',
                      ready_for_user_action=True, tick=tick, t=boot-100-.25,
                      realtime=boot+900-.25, remaining_boottime_seconds=request['max_seconds']+100-boot)
        observations.append(dict(status=status, process=dict(state='alive', pid=123, start_ticks=456,
                    argv=request['argv']), remote_realtime=boot+900, remote_boottime=boot))
    return dict(identity_unchanged=True, launch_receipt=receipt, clock_start={'boot': 100},
                observations=observations, host_roundtrip_seconds=2.3)


class FakeSSH:
    def __init__(self): self.calls = []
    def __call__(self, command, **kwargs):
        request = json.loads(kwargs['input']); self.calls.append(request)
        if request['action'] == 'launch':
            value = {'launched': True, 'launch_receipt': ready_data(request)['launch_receipt']}
        elif request['action'] == 'status': value = ready_data(request)
        else:
            raw = b'{"raw":"original"}\n'
            value = dict(identity_unchanged=True, cleanup_state=dict(exact_worker_state='absent',
                        worker_terminal=True, monitor_started=True, monitor_errors=[], dbus_returncode=-15),
                        files={'capture/capture-private.json': dict(base64=base64.b64encode(raw).decode(),
                                                                    sha256=launcher.sha(raw))})
        return SimpleNamespace(returncode=0, stdout=json.dumps(value).encode(), stderr=b'')


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.pins = self.root / 'pins.json'
        self.entries = json.loads(launcher.PINS.read_bytes())
        for name, entry in self.entries.items():
            if name != 'transport':
                target = self.root / (name + '.json'); target.write_bytes(Path(entry['path']).read_bytes())
                entry['path'] = str(target)
        self.save_pins()
        self.migration = self.root / 'migration.json'
        self.migration.write_text(json.dumps(dict(schema='charging-icon-r7-migration-tests-v1', passed=True,
            launcher_sha256=launcher.sha((HERE/'launcher.py').read_bytes()),
            identity_pins_sha256=launcher.sha(self.pins.read_bytes()), sha256=launcher.FROZEN,
            manifest_sha256=launcher.MANIFEST)))
        self.ssh = FakeSSH(); self.txn = 'charging-icon-r7-directed-test'

    def save_pins(self): self.pins.write_text(json.dumps(self.entries))
    def edit(self, name, key, value):
        entry = self.entries[name]; target = Path(entry['path'])
        data = json.loads(target.read_bytes()); data[key] = value
        target.write_text(json.dumps(data)); entry['sha256'] = launcher.sha(target.read_bytes()); self.save_pins()
    def action(self, action, confirmed=False):
        return launcher.run(action, self.txn, confirmed, ssh=self.ssh, private=self.root/'output',
                            pins=self.pins, migration=self.migration)

    def test_unchanged_worker_audit_and_historical_receipts_are_explicit(self):
        old = HERE.parent / 'icon-capture-candidate'
        for name in ['worker.py', 'audit.py']:
            self.assertEqual((HERE/name).read_bytes(), (old/name).read_bytes())
        self.assertEqual((HERE/'baseline-test-result.json').read_bytes(), (old/'test-result.json').read_bytes())
        self.assertEqual((HERE/'baseline-launcher-test-result.json').read_bytes(), (old/'launcher-test-result.json').read_bytes())
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('read on import')), \
             patch('subprocess.run', side_effect=AssertionError('network on import')):
            load(HERE/'launcher.py', 'r7_inert')
        compile(launcher.REMOTE, '<r7-rpc>', 'exec')

    def test_r7_boot_guard_manifest_and_180_second_once_only_launch(self):
        files, boot, guard = launcher.adopt_local(HERE, self.pins, self.migration)
        self.assertEqual(boot, json.loads(Path(self.entries['endpoint']['path']).read_bytes())['observed_new_boot'])
        self.assertEqual(guard, json.loads(Path(self.entries['adoption']['path']).read_bytes())['guard_path'])
        self.assertEqual(inspect.signature(launcher.run).parameters['max_seconds'].default, 180)
        with self.assertRaises(ValueError): self.action('launch')
        self.assertFalse(self.ssh.calls)
        self.assertTrue(self.action('launch', True)['launch_receipt_verified'])
        request = self.ssh.calls[0]
        self.assertEqual(request['max_seconds'], 180); self.assertEqual(request['manifest_sha256'], launcher.MANIFEST)
        self.assertIn('/icon-capture-r7/', request['remote_output'])
        self.assertEqual(request['files'], launcher.FROZEN)
        with self.assertRaises(FileExistsError): self.action('launch', True)
        self.assertEqual(len(self.ssh.calls), 1)

    def test_affected_identity_semantics_and_tamper_reject(self):
        original = copy.deepcopy(self.entries)
        edits = [('endpoint','observed_new_boot','11111111-2222-4333-8444-555555555555'),
                 ('endpoint','peer','169.254.42.1'), ('endpoint','original_key_verified',False),
                 ('adoption','charging_manifest_sha256','944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'),
                 ('adoption','guard_path','/var/lib/samurai/old/boot-id-private.txt'),
                 ('adopt_result','guard_created',False), ('postboot','passed',False),
                 ('probe','boot_id','11111111-2222-4333-8444-555555555555')]
        for name,key,value in edits:
            with self.subTest(name=name, key=key):
                self.entries = copy.deepcopy(original)
                for n,e in self.entries.items():
                    if n != 'transport': Path(e['path']).write_bytes(Path(json.loads(launcher.PINS.read_bytes())[n]['path']).read_bytes())
                self.edit(name,key,value)
                with self.assertRaises(ValueError): launcher.reviewed_identity(self.pins)
        self.assertFalse(self.ssh.calls)

    def test_actual_transport_is_strict_original_key_ipv6_without_fallback(self):
        call = launcher.transport()
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=b'{}', stderr=b'')) as run:
            call('read-only-test', input=b'{}', timeout=7)
        argv = run.call_args.args[0]
        self.assertIn('-6', argv); self.assertIn('HostKeyAlias=169.254.42.1', argv)
        for option in ['StrictHostKeyChecking=yes','IdentitiesOnly=yes','BatchMode=yes']:
            self.assertIn(option, argv)
        self.assertEqual(argv[-2], 'root@fe80::62:bcff:fe28:a101%29')
        self.assertEqual(run.call_count, 1)

    def test_180s_readiness_requires_new_tick_exact_pid_and_current_time(self):
        self.action('launch', True); request = self.ssh.calls[0]
        good = ready_data(request); self.assertTrue(launcher.ready_check(good, request)['may_prompt_user'])
        for key,value in [('tick',10), ('remaining_boottime_seconds',44), ('realtime',1000)]:
            data = copy.deepcopy(good); data['observations'][1]['status'][key] = value
            self.assertFalse(launcher.ready_check(data,request)['may_prompt_user'])
        data = copy.deepcopy(good); data['observations'][1]['process']['start_ticks'] += 1
        self.assertFalse(launcher.ready_check(data,request)['may_prompt_user'])
        self.assertTrue(self.action('status')['may_prompt_user'])

    def test_actual_capture_waits_for_late_real_edges_then_25s_not_stable_idle(self):
        boundary = historical.FakeIO(lambda t: historical.sample(t,0,0) if 100 <= t <= 109 else historical.sample(t))
        config = dict(historical.CONFIG, max_seconds=180, manifest_sha256=launcher.MANIFEST,
                      transaction=self.txn, boot_id=launcher.reviewed_identity(self.pins)[0])
        result = worker.run(config,boundary,audit.audit)
        self.assertTrue(result['physical_cycle_passed']); self.assertEqual(result['terminal_reason'],'cycle_complete')
        self.assertEqual(boundary.saved['capture-private.json']['duration_seconds'],137)
        self.assertEqual(result['raw_cycle_evidence']['offline_begin'],100)
        self.assertEqual(result['raw_cycle_evidence']['online_begin'],110)
        self.assertEqual(result['raw_cycle_evidence']['online_span'],27)
        self.assertFalse(result['screen_latency_verified'])
        self.assertTrue(all(r['status']=='Discharging' and r['current_now_ua']==-4000
                            for r in result['sample_status_current_sequence']))
        self.assertTrue(all(e['source_to_first_following_display_state_event_seconds_estimated'] is None
                            for e in result['edges']))

    def test_180s_no_physical_edge_or_mixed_source_cannot_pass(self):
        def configured(t):
            row=historical.sample(t);row['udc_state']='configured';row['telemetry']['budget_ua']=0
            return row
        for samples in [configured, lambda t:historical.sample(t,0,1) if 100<=t<=109 else historical.sample(t)]:
            boundary=historical.FakeIO(samples)
            result=worker.run(dict(historical.CONFIG,max_seconds=180),boundary,audit.audit)
            self.assertFalse(result['physical_cycle_passed']);self.assertEqual(result['terminal_reason'],'deadline')
            self.assertEqual(boundary.saved['capture-private.json']['duration_seconds'],180)
            self.assertFalse(boundary.statuses[-1]['active']);self.assertEqual(boundary.stopped,1)

    def test_fetch_is_read_only_terminal_gate_and_retains_original_bytes(self):
        self.action('launch', True); result=self.action('fetch')
        self.assertTrue(result['cleanup_confirmed']);self.assertFalse(result['may_prompt_user'])
        retained=Path(result['retained_directory'])/'capture/capture-private.json'
        self.assertEqual(retained.read_bytes(),b'{"raw":"original"}\n')
        self.assertEqual([q['action'] for q in self.ssh.calls],['launch','fetch'])
        state=dict(exact_worker_state='alive',worker_terminal=False,monitor_started=True,monitor_errors=[],dbus_returncode=-15)
        self.assertFalse(launcher.cleanup_check(state))


if __name__=='__main__': unittest.main(verbosity=2)
