"""Only launcher/ready boundaries; no network and no repeat of collector tests."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('icon_launcher', HERE / 'launcher.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)


def request():
    return {'transaction': 'charging-icon-future-test', 'token': 'test-token', 'expected_boot': 'adopted',
            'manifest_sha256': launcher.MANIFEST, 'files': launcher.FROZEN, 'max_seconds': 300,
            'argv': ['python3', '/own/worker.py', '--transaction', 'charging-icon-future-test']}


def ready_data(req=None):
    req = req or request()
    receipt = {k: req[k] for k in ['transaction', 'token', 'expected_boot', 'manifest_sha256', 'files', 'argv']}
    receipt.update(pid=123, start_ticks=900)
    observations = []
    for tick, boot in [(10, 110.25), (12, 112.45)]:
        status = {'pid': 123, 'start_ticks': 900, 'active': True, 'terminal': False, 'phase': 'ready',
                  'ready_for_user_action': True, 'tick': tick, 't': boot - 100 - .25,
                  'realtime': boot + 900 - .25, 'remaining_boottime_seconds': 400 - boot}
        observations.append({'status': status, 'process': {'state': 'alive', 'pid': 123, 'start_ticks': 900,
                             'argv': req['argv']}, 'remote_realtime': boot + 900, 'remote_boottime': boot})
    return {'identity_unchanged': True, 'launch_receipt': receipt, 'clock_start': {'boot': 100},
            'observations': observations, 'host_roundtrip_seconds': 2.3, 'host_received_realtime': 1012.6}


class FakeTransport:
    def __init__(self): self.calls = []; self.failure = None; self.reply = None
    def __call__(self, command, **kwargs):
        incoming = json.loads(kwargs['input']); self.calls.append(incoming)
        if self.failure: raise self.failure
        if self.reply is not None: data = self.reply
        elif incoming['action'] == 'launch': data = {'launched': True, 'launch_receipt': ready_data(incoming)['launch_receipt']}
        elif incoming['action'] == 'status': data = ready_data(incoming)
        else:
            raw = b'{"raw":"original bytes"}\n'
            data = {'identity_unchanged': True, 'cleanup_state': {'exact_worker_state': 'absent',
                    'worker_terminal': True, 'monitor_started': True, 'monitor_errors': [], 'dbus_returncode': -15},
                    'files': {'capture/capture-private.json': {'base64': base64.b64encode(raw).decode(),
                                                               'sha256': launcher.sha(raw)}}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(data).encode(), stderr=b'')


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.private = self.root / 'private'
        self.recovery = self.root / 'snapshot-private.json'
        self.recovery.write_text(json.dumps({'boot_id': '11111111-2222-4333-8444-555555555555',
              'result': {'terminal': True, 'worker_exited': True, 'restored': True, 'same_boot': True}}))
        self.adoption = self.root / 'adoption-private.json'
        self.adoption.write_text(json.dumps({'original_key_verified': True, 'baseline440_verified': True,
                                            'guard_path': '/var/lib/samurai/test/boot-id-private.txt'}))
        patcher = patch.object(launcher, 'RECOVERY_SHA', launcher.sha(self.recovery.read_bytes()))
        patcher.start(); self.addCleanup(patcher.stop)
        self.ssh = FakeTransport(); self.txn = 'charging-icon-future-test'

    def run_action(self, action, confirmed=False):
        return launcher.run(action, self.txn, confirmed, ssh=self.ssh, private=self.private,
                            recovery=self.recovery, adoption=self.adoption)

    def test_import_inert_and_remote_python_syntax(self):
        fresh = importlib.util.module_from_spec(spec)
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('read on import')), \
             patch('subprocess.Popen', side_effect=AssertionError('spawn on import')):
            spec.loader.exec_module(fresh)
        compile(launcher.REMOTE, '<remote-rpc>', 'exec')

    def test_unconfirmed_launch_reads_nothing_and_calls_no_transport(self):
        with patch.object(launcher, 'adopt_local', side_effect=AssertionError('preflight too early')):
            with self.assertRaises(ValueError): self.run_action('launch')
        self.assertFalse(self.ssh.calls); self.assertFalse(self.private.exists())

    def test_launch_adopts_frozen_bundle_boot_guard_once(self):
        result = self.run_action('launch', True)
        self.assertTrue(result['launched']); self.assertFalse(result['may_prompt_user'])
        self.assertTrue(result['launch_receipt_verified']); self.assertEqual(result['pid'], 123)
        incoming = self.ssh.calls[0]
        self.assertEqual(incoming['expected_boot'], '11111111-2222-4333-8444-555555555555')
        self.assertEqual(incoming['guard_path'], '/var/lib/samurai/test/boot-id-private.txt')
        self.assertEqual(incoming['manifest_sha256'], launcher.MANIFEST)
        for name, raw in incoming['file_base64'].items():
            self.assertEqual(launcher.sha(base64.b64decode(raw)), launcher.FROZEN[name])
        marker = self.private / self.txn / 'launch-request-private.json'
        before = marker.read_bytes()
        with self.assertRaises(FileExistsError): self.run_action('launch', True)
        self.assertEqual(marker.read_bytes(), before); self.assertEqual(len(self.ssh.calls), 1)

    def test_unknown_launch_outcome_persists_marker_and_never_relaunches(self):
        self.ssh.failure = TimeoutError('unknown SSH outcome')
        with self.assertRaises(TimeoutError): self.run_action('launch', True)
        self.assertTrue((self.private / self.txn / 'launch-request-private.json').exists())
        with self.assertRaises(FileExistsError): self.run_action('launch', True)
        self.assertEqual(len(self.ssh.calls), 1)
        self.ssh.failure = None
        result = self.run_action('fetch')
        self.assertTrue(result['fetched']); self.assertEqual(len(self.ssh.calls), 2)

    def test_wrong_snapshot_or_bundle_refuses_before_transport(self):
        for which in ['snapshot', 'bundle']:
            with self.subTest(which=which):
                if which == 'snapshot':
                    with patch.object(launcher, 'RECOVERY_SHA', '0' * 64):
                        with self.assertRaises(ValueError): self.run_action('launch', True)
                else:
                    changed = {**launcher.FROZEN, 'worker.py': '0' * 64}
                    with patch.object(launcher, 'FROZEN', changed):
                        with self.assertRaises(ValueError): self.run_action('launch', True)
        self.assertFalse(self.ssh.calls); self.assertFalse(self.private.exists())

    def test_status_needs_existing_marker_and_only_status_can_allow_prompt(self):
        with self.assertRaises(FileNotFoundError): self.run_action('status')
        self.assertFalse(self.ssh.calls)
        self.run_action('launch', True)
        result = self.run_action('status')
        self.assertTrue(result['may_prompt_user'])
        self.assertEqual([q['action'] for q in self.ssh.calls], ['launch', 'status'])

    def test_real_ready_checker_accepts_only_two_current_exact_observations(self):
        self.assertTrue(launcher.ready_check(ready_data(), request())['may_prompt_user'])
        for count in [0, 1, 3]:
            data = ready_data(); data['observations'] = data['observations'][:count] if count < 3 else data['observations'] * 2
            self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])

    def test_ready_refuses_pid_reuse_cmdline_and_receipt_mismatch(self):
        edits = [('state', 'pid_reused'), ('start_ticks', 901), ('argv', ['python3', '/other/worker.py']), ('pid', 999)]
        for key, value in edits:
            data = ready_data(); data['observations'][1]['process'][key] = value
            self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])
        for key, value in [('token', 'other'), ('pid', None), ('start_ticks', 0), ('files', {})]:
            data = ready_data(); data['launch_receipt'][key] = value
            self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])

    def test_ready_refuses_stale_nonadvancing_unready_or_short_deadline(self):
        for key, value in [('realtime', 1000), ('tick', 10), ('t', 10), ('active', False),
                           ('terminal', True), ('ready_for_user_action', False), ('phase', 'settling'),
                           ('remaining_boottime_seconds', 44), ('remaining_boottime_seconds', float('nan'))]:
            data = ready_data(); data['observations'][1]['status'][key] = value
            self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])
        data = ready_data(); data['clock_start']['boot'] -= 250
        self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])
        data = ready_data(); data['identity_unchanged'] = False
        self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])

    def test_ready_refuses_missing_timing_future_status_and_bad_spacing(self):
        for edit in ['missing', 'future', 'spacing', 'old_rpc']:
            data = ready_data()
            if edit == 'missing': del data['observations'][1]['remote_boottime']
            elif edit == 'future': data['observations'][1]['status']['realtime'] += 10
            elif edit == 'spacing': data['observations'][1]['remote_boottime'] += 10
            else: data['host_roundtrip_seconds'] = 9
            self.assertFalse(launcher.ready_check(data, request())['may_prompt_user'])

    def test_fetch_preserves_byte_originals_each_time_without_stop_action(self):
        self.run_action('launch', True)
        one = self.run_action('fetch'); two = self.run_action('fetch')
        self.assertNotEqual(one['retained_directory'], two['retained_directory'])
        for result in [one, two]:
            self.assertFalse(result['may_prompt_user']); self.assertTrue(result['cleanup_confirmed'])
            path = Path(result['retained_directory']) / 'capture/capture-private.json'
            self.assertEqual(path.read_bytes(), b'{"raw":"original bytes"}\n')
        self.assertEqual([q['action'] for q in self.ssh.calls], ['launch', 'fetch', 'fetch'])

    def test_cleanup_requires_terminal_exited_worker_and_monitor_receipt(self):
        good = dict(exact_worker_state='absent', worker_terminal=True, monitor_started=True,
                    monitor_errors=[], dbus_returncode=-15)
        self.assertTrue(launcher.cleanup_check(good))
        for key, value in [('exact_worker_state', 'alive'), ('exact_worker_state', 'unknown'),
                           ('worker_terminal', False), ('monitor_started', None),
                           ('monitor_errors', ['forced cleanup']), ('dbus_returncode', None)]:
            self.assertFalse(launcher.cleanup_check({**good, key: value}))

    def test_fetch_rejects_traversal_or_bad_hash_preserving_response(self):
        self.run_action('launch', True)
        for name in ['../outside', 'capture/../../outside', 'capture\\outside', 'C:/outside']:
            data = {'files': {name: {'base64': 'eA==', 'sha256': launcher.sha(b'x')}}}
            with self.assertRaises(ValueError): launcher.retain_fetch(data, self.private / self.txn)
        data = {'files': {'capture/raw.log': {'base64': 'eA==', 'sha256': '0' * 64}}}
        self.ssh.reply = data
        with self.assertRaises(ValueError): self.run_action('fetch')
        self.assertTrue(list((self.private / self.txn).glob('fetch-*-stdout-private.json')))


if __name__ == '__main__': unittest.main(verbosity=2)
