"""Only new request/trace/classification boundaries, never live IO or old suites."""
from pathlib import Path
import ast
import copy
import errno
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


trace = load('pm_new_trace', HERE / 'trace-evidence.py')
worker = load('pm_new_worker', HERE / 'worker.py')
prepare = load('pm_new_prepare', HERE / 'prepare-request.py')
inventory_path = Path('E:/edk2-samurai-out/charging-management-20261023/pm-r5-recovery/console-inventory-private.json')
inventory_raw = inventory_path.read_bytes()
assert sha(inventory_raw) == '90fe8ea9ea7af9b0a170936acce8b0b93bee4d2e7d4fac5a1165af0d3083aec4'
inventory = json.loads(inventory_raw)


class FakeTraceIO:
    def __init__(self):
        self.values = {'/proc/interrupts': ' CPU0 CPU1\n 88: 4 6 GIC pm8xxx_rtc_alarm\n',
                       '/trace/available_events': ' '.join(inventory['selected_available_events']),
                       '/trace/trace_clock': 'local [global] boot mono',
                       '/trace/events/sched/sched_switch/trigger': inventory['sched_stacktrace_trigger_catalog']}
        for name in trace.REQUIRED:
            self.values['/trace/events/' + name + '/format'] = inventory['selected_formats'][name]
        self.writes, self.directories, self.removed = [], set(), []
        self.fail = None

    def read(self, path):
        if path == '/sys/power/pm_wakeup_irq':
            raise FileNotFoundError(errno.ENOENT, 'not compiled/exposed')
        if '/instances/' in path and '/events/' in path and path.endswith('/format'):
            return self.values['/trace/events/' + path.split('/events/', 1)[1]]
        return self.values[path]

    def write(self, path, value):
        self.writes.append((path, value))
        if path.endswith('/trace_clock'):
            self.values[path] = 'local [' + value + '] global mono'
        elif path.endswith('/trigger'):
            self.values[path] = '# Available triggers: stacktrace\n' if value == '!stacktrace' else value.replace('stacktrace:128', 'stacktrace:count=128')
        else:
            self.values[path] = value
        if self.fail and self.fail(path, value):
            raise OSError(errno.EIO, 'injected after possible mutation')

    def mkdir(self, path):
        if path in self.directories:
            raise FileExistsError(path)
        self.directories.add(path)
        self.values[path + '/trace'] = '# entries-in-buffer/entries-written: 1/1\n'

    def rmdir(self, path):
        self.removed.append(path)
        self.directories.remove(path)


def capability(io=None):
    return trace.inspect(io or FakeTraceIO(), 123, (), root='/trace')


def setup_session(io):
    session = trace.Session(io, capability(io), 'charging-pm-current-fixture', lambda text: None)
    with patch.object(trace.time, 'CLOCK_BOOTTIME', 7, create=True), patch.object(trace.time, 'clock_gettime', return_value=100, create=True):
        session.setup()
    return session


def request_fixture(root):
    txn = root / 'image502-notify-live-001'
    txn.mkdir()
    context, observed, adoption = txn / 'host-context-private.json', txn / 'postboot', txn / 'adoption-01-private'
    context.write_text('{}'); observed.mkdir(); adoption.mkdir()
    d = {'schema': 'samurai-image502-adoption-v1', 'transaction_id': txn.name,
         'boot': '00000000-0000-0000-0000-000000000502',
         'guard': '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt',
         'version': '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'release': '7.3.0-rc6-rmx1931-samurai-k363+',
         'rootfs': '1' * 64, 'serial_sha256': '2' * 64, 'compatible_sha256': '3' * 64, 'notes': {},
         'manifest': '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f',
         'candidate_boot_sha256': '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
         'candidate_logdump_sha256': 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
         'postboot_raw_sha256': '4' * 64, 'postboot_request': {}}
    pointer = {'guard_path': d['guard'], 'Image502_verified': True, 'original_key_verified': True,
               'baseline481_verified': True, 'charging_manifest_sha256': d['manifest'],
               'candidate_boot_sha256': d['candidate_boot_sha256'], 'candidate_logdump_sha256': d['candidate_logdump_sha256'],
               'postboot_raw_sha256': d['postboot_raw_sha256']}
    def save(name, obj):
        (adoption / name).write_text(json.dumps(obj))
    save('adopt-request-private.json', d)
    save('adoption-result-private.json', {'passed': True, 'guard_created': True, 'old_pointer_backup_preserved': True,
                                         'old_guards_preserved': True, 'pointer': pointer})
    save('adopt-transport-terminal-private.json', {'terminal': True, 'returncode': 0, 'pid': 500})
    save('adopt-stdout-private.json', {'guard_created': True, 'fresh_validation_passed': True,
                                      'boot_and_logdump_verified': True, 'transaction_id': d['transaction_id'],
                                      'boot_id': d['boot'], 'guard': d['guard'], 'postboot_raw_sha256': d['postboot_raw_sha256']})
    save('new-endpoint-private.json', {'postboot_Image502_passed': True, 'original_key_verified': True,
                                      'observed_new_boot': d['boot'], 'guard_path': d['guard'],
                                      'peer': 'fe80::62:bcff:fe28:a101%29', 'interface_index': 29, 'host_key_alias': '169.254.42.1'})
    (adoption / 'executed-adoption-source.py').write_bytes(b'reviewed-fixture-payload')
    p = root / 'pointer.json'; p.write_text(json.dumps(pointer))
    reviewer = types.SimpleNamespace(review=lambda c, o: (copy.deepcopy(d), {}), payload=lambda x, s: b'reviewed-fixture-payload')
    c = prepare.build_request(context, observed, adoption, 'charging-pm-current-fixture', str(root / 'remote-output'), reviewer=reviewer, pointer=p)
    return c, adoption, pointer, p, (context, observed, reviewer)


def sample(c):
    return {'boot_id': c['adopted']['boot'], 'release': c['adopted']['release'], 'manifest_sha256': c['adopted']['manifest'],
            'adopted_identity_verified': True, 'modules_exact': True, 'postboot_profile_passed': True,
            'charging_profile_healthy': True, 'read_only_prerequisites': True,
            'trace_capability': capability(), 'wakeup_irq': {'available': False, 'value': None, 'errno': 2},
            'rtc_irq': 10, 'stats': {'success': 3, 'fail': 0}, 'dmesg': 'first\nsecond\nlast\n',
            'allowance': 500000, 'source': {'current_max': '1500000'}, 'hardware_input': {'input_current_limit': '900000'}, 'udc': {'state': 'configured'},
            'sample': {'valid': 1, 'online': 1, 'protection_ok': 1, 'desired_enable': 1, 'shadow': 0,
                       'age_ms': 10, 'budget_ua': 1500000, 'error': 0, 'stop_error': 0, 'latched': 0, 'source_inhibit': 0, 'fault': 0},
            'state': {'taint': '0', 'driver': 'samurai-mp2650', 'camera_pm': {n: 'suspended' for n in worker.CAMERA},
                      'm2m': json.dumps(dict(users=0, running=False, fatal=False, pinned=False, orphans=0, first_error=0)),
                      'services': [dict(comm=n, pid=i + 100, uid=10000) for i, n in enumerate(worker.SERVICES)], 'registers': {'08': 0x10}}}


def trace_text():
    rows = ['# entries-in-buffer/entries-written: 20/20', ' x 1.000: suspend_resume: machine_suspend[0] begin',
            ' x 1.500: irq_handler_entry: irq=88 name=pm8xxx_rtc_alarm', ' x 1.600: suspend_resume: machine_suspend[0] end']
    drivers = [('0-005c', 'samurai-mp2650'), ('samurai-usb-input', 'samurai-usb-input'), ('samurai-gauge-protection', 'samurai-gauge-protection'), ('5-0055', 'bq27xxx-battery')]
    for phase, ordered, base in [('suspend', drivers, .1), ('resume', list(reversed(drivers)), 2)]:
        for i, (device, driver) in enumerate(ordered):
            t = base + i / 5
            rows += [f' x {t:.3f}: device_pm_callback_start: {driver} {device}, parent: bus, driver [{phase}]',
                     f' x {t + .01:.3f}: device_pm_callback_end: {driver} {device}, err=0']
    return '\n'.join(rows)


class FakeBoard:
    def __init__(self, c):
        self.before = sample(c); self.after = copy.deepcopy(self.before)
        self.after.update(rtc_irq=11, dmesg='second\nlast\nresume\n')
        self.after['stats']['success'] = 4
        self.primitive = {'outcome': 'returned', 'mem_returned': True, 'cleanup': 'alarm_already_consumed_or_cleared', 'estimated_residency_seconds': 15}
        self.calls, self.saved, self.fail = [], {}, None
    def create_new(self, c): self.calls.append('create')
    def save(self, name, data): self.saved[name] = copy.deepcopy(data)
    def capture(self, c, before):
        self.calls.append('before' if before else 'after')
        if not before and self.fail == 'post': raise OSError('post evidence unavailable')
        return copy.deepcopy(self.before if before else self.after)
    def start_trace(self, cap): self.calls.append('trace')
    def suspend_once(self): self.calls.append('mem'); return self.primitive
    def finish_trace(self): return trace_text(), {}
    def cleanup_trace_if_owned(self):
        if self.fail == 'cleanup': raise OSError('cleanup failed')
        return {'passed': True, 'owned': True}
    def wait_for_fresh_sample(self): pass


class NewBoundaryTests(unittest.TestCase):
    def test_request_requires_actual_completed_adoption_and_current_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, a, pointer, p, args = request_fixture(Path(tmp))
            worker.validate_request(c)
            pointer['Image502_verified'] = False; p.write_text(json.dumps(pointer))
            with self.assertRaises(ValueError): prepare.build_request(args[0], args[1], a, c['transaction'], c['output_root'], reviewer=args[2], pointer=p)
            pointer['Image502_verified'] = True; p.write_text(json.dumps(pointer))
            r = json.loads((a / 'adoption-result-private.json').read_bytes()); r['passed'] = False
            (a / 'adoption-result-private.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError): prepare.build_request(args[0], args[1], a, c['transaction'], c['output_root'], reviewer=args[2], pointer=p)

    def test_actual_cached_runtime_formats_and_missing_reason_are_not_zero(self):
        cap = capability()
        self.assertTrue(cap['passed']); self.assertEqual(cap['wakeup_irq'], {'available': False, 'value': None, 'errno': 2})
        self.assertEqual(trace.fields(inventory['selected_formats']['irq/irq_handler_entry']) & {'irq', 'name'}, {'irq', 'name'})

    def test_ambiguous_irq_or_missing_format_rejects_before_any_write(self):
        for bad in ['irq', 'format']:
            io = FakeTraceIO()
            if bad == 'irq': io.values['/proc/interrupts'] += ' 89: 1 GIC pm8xxx_rtc_alarm\n'
            else: io.values['/trace/events/irq/irq_handler_exit/format'] = 'field:int ret;'
            cap = capability(io); self.assertFalse(cap['passed'])
            s = trace.Session(io, cap, 'charging-pm-current-fixture', lambda text: None)
            with self.assertRaises(ValueError): s.setup()
            self.assertEqual(io.writes, [])

    def test_exact_filter_all_installed_before_enables_and_expiry_before_arm(self):
        io = FakeTraceIO(); s = setup_session(io)
        self.assertEqual([v for p, v in io.writes if '/irq/' in p and p.endswith('/filter')], ['irq == 88', 'irq == 88'])
        s.ready_to_arm()
        io.values[s.path + '/events/sched/sched_switch/trigger'] = 'stacktrace:count=0 if ' + s.trigger_condition
        with self.assertRaises(ValueError): s.ready_to_arm()
        self.assertTrue(s.cleanup()['passed'])
        self.assertTrue(all(v in ('1', '0') for p, v in io.writes if p.endswith('/enable')))

    def test_partial_filter_write_failure_never_enables_and_only_owned_cleanup(self):
        io = FakeTraceIO(); io.fail = lambda p, v: p.endswith('/irq_handler_exit/filter') and v != '0'
        s = trace.Session(io, capability(io), 'charging-pm-current-fixture', lambda text: None)
        with self.assertRaises(OSError): s.setup()
        self.assertFalse(any(v == '1' for p, v in io.writes if p.endswith('/enable')))
        self.assertTrue(s.cleanup()['passed']); self.assertEqual(io.removed, [s.path])
        io = FakeTraceIO(); io.directories.add(s.path)
        s = trace.Session(io, capability(io), 'charging-pm-current-fixture', lambda text: None)
        with self.assertRaises(FileExistsError): s.setup()
        self.assertIsNone(s.cleanup()); self.assertEqual(io.removed, [])

    def test_observed_adapter_checks_before_arm_but_allows_own_alarm_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, *_ = request_fixture(Path(tmp))
            # Only the Linux module-import boundary is absent on Windows.
            with patch.dict(sys.modules, {'fcntl': types.ModuleType('fcntl')}):
                b = worker.RealBoard(c)
            b.trace = types.SimpleNamespace(ready_to_arm=lambda: (_ for _ in ()).throw(ValueError('not ready')))
            writes = []
            with patch.object(b.pm.SysfsPMIO, 'write_alarm', side_effect=lambda value: writes.append(value)):
                with self.assertRaises(ValueError): b.io.write_alarm(123)
                b.io.write_alarm(0)
            self.assertEqual(writes, [0])

    def test_irq_timing_reason_and_functional_facts_are_independent(self):
        for when, expected in [('1.500', True), ('0.900', False), ('2.100', False)]:
            text = trace_text().replace('1.500:', when + ':') + '\n x 0.050: rtc_set_alarm: UTC (12345) (0)\n x 0.060: rtc_alarm_irq_enable: enable RTC alarm IRQ (0)'
            value = trace.analyze(text, {'mem_returned': True, 'estimated_residency_seconds': 15, 'alarm_target': 12345}, capability(), {'available': False, 'value': None, 'errno': 2})
            self.assertEqual(value['rtc_irq_during_machine_suspend_observed'], expected)
            self.assertTrue(value['returned']); self.assertFalse(value['unique_wakeup_reason']['proved'])
            self.assertTrue(value['own_target_set_event_observed']); self.assertTrue(value['RTC_alarm_enable_events'][0]['enabled'])

    def test_plan_15_plus_minus_5_boundaries_preserve_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, *_ = request_fixture(Path(tmp))
            for duration, expected in [(9.99, False), (10, True), (20, True), (20.01, False)]:
                b = FakeBoard(c); b.primitive['estimated_residency_seconds'] = duration
                r = worker.dispatch(c, b)
                self.assertEqual(r['functional_checks']['planned_residency_observed'], expected)
                self.assertTrue(r['functional_facts']['returned']); self.assertFalse(r['whole_system_accepted'])
                self.assertEqual(b.calls.count('mem'), 1)

    def test_missing_trace_preflight_does_not_mem_and_post_cleanup_failures_keep_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            c, *_ = request_fixture(Path(tmp)); b = FakeBoard(c)
            b.before['trace_capability'].update(passed=False, errors=['format absent'])
            r = worker.dispatch(c, b); self.assertNotIn('mem', b.calls)
            for failure in ['post', 'cleanup']:
                b = FakeBoard(c); b.fail = failure; r = worker.dispatch(c, b)
                self.assertTrue(r['functional_facts']['returned']); self.assertEqual(r['functional_facts']['estimated_residency_seconds'], 15)
                self.assertFalse(r['whole_system_accepted']); self.assertIn('result.json', b.saved)

    def test_reuse_exact_primitive_unchanged_functions_and_log_overlap(self):
        self.assertEqual(sha((HERE / 'pm-transaction.py').read_bytes()), worker.PRIMITIVE_SHA256)
        def functions(path):
            text = path.read_text(); return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
        old = functions(REF / 'charging-ui-audit-20261023/pm-worker-candidate/worker.py')
        new = functions(HERE / 'worker.py')
        for name in ['healthy', 'services', 'configuration_preserved', 'audit_trace']: self.assertEqual(old[name], new[name])
        proof = trace.log_suffix('a\nb\nc\n', 'b\nc\nd\n'); self.assertTrue(proof['complete_since_baseline']); self.assertEqual(proof['new_lines'], ['d'])
        self.assertFalse(trace.log_suffix('a\nb\nc\n', 'a\nb\nd\n')['complete_since_baseline'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NewBoundaryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {'passed': result.wasSuccessful(), 'new_test_methods': result.testsRun,
               'scope': 'new actual request, runtime-format/filtered-trace ownership, arm guard, timing/result boundaries only; fake filesystem/OS',
               'actual_r5_runtime_format_source_sha256': sha(inventory_raw),
               'tested_files': {n: sha((HERE / n).read_bytes()) for n in ['prepare-request.py', 'worker.py', 'trace-evidence.py', 'pm-transaction.py', 'test-new-boundaries.py']},
               'old27_29_126_rerun': False, 'device_trace_PM_build_SDK_Git': False,
               'synthetic_adoption_is_not_runtime_request': True}
    (HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
