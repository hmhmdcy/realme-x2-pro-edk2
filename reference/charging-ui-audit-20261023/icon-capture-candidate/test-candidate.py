"""Host-only tests: real scheduler/auditor with fake OS boundaries, no device."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
def load(name):
    spec = importlib.util.spec_from_file_location('icon_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


worker, audit = load('worker'), load('audit')


def sample(t, source=1, acok=1):
    telemetry = dict(valid=1, online=source, protection_ok=1, shadow=0, age_ms=100,
                     error=0, stop_error=0, latched=0, source_inhibit=0, fault=0,
                     flags=0x108, desired_enable=1)
    return {'t_start': t, 't_end': t, 'source_online': source, 'acok_online': acok,
            'telemetry': telemetry, 'flags_fresh': bool(source == acok == 1),
            'battery': {'status': 'Discharging', 'current_now_ua': -4000}}


def signal(t, path, values, interface='org.freedesktop.UPower.Device'):
    fields = ''.join('      dict entry(\n         string ' + json.dumps(k) + '\n         variant             '
                     + kind + ' ' + str(value) + '\n      )\n' for k, (kind, value) in values.items())
    return ('signal time=' + str(t) + ' sender=:1.8 -> destination=(null destination) serial=1 '
            'path=' + path + '; interface=org.freedesktop.DBus.Properties; member=PropertiesChanged\n'
            '   string ' + json.dumps(interface) + '\n   array [\n' + fields + '   ]\n   array [\n   ]\n')


class FakeIO:
    def __init__(self, rows=None):
        self.now = 100; self.boot_extra = 0; self.saved = {}; self.statuses = []; self.appended = []
        self.created = self.discovered = self.started = self.stopped = 0
        self.rows = rows or (lambda t: sample(t, 0, 0) if 4 <= t <= 6 else sample(t))
        self.fail_sample = self.fail_alive = None; self.fail_identity = self.fail_discovery = False
        self.fail_cleanup = self.fail_event_data = False
    def create_new(self, c):
        if self.created: raise FileExistsError('existing transaction')
        self.created += 1
    def check_identity(self, c):
        if self.fail_identity: raise ValueError('wrong adopted identity')
    def discover_battery(self):
        self.discovered += 1
        if self.fail_discovery: raise ValueError('ambiguous actual Battery')
    def monotonic(self): return self.now
    def boottime(self): return self.now + self.boot_extra
    def clock_pair(self): return {'m0': self.now, 'm1': self.now, 'real': self.now + 900,
                                  'boot': self.boottime()}
    def start_events(self, base): self.started += 1
    def events_alive(self): return len(self.appended) != self.fail_alive
    def sample(self, base):
        if len(self.appended) == self.fail_sample: raise OSError('read failed')
        return self.rows(self.now - base)
    def append_sample(self, row): self.appended.append(copy.deepcopy(row))
    def status(self, data): self.statuses.append(copy.deepcopy(data))
    def sleep(self, seconds): self.now += seconds
    def stop_events(self):
        self.stopped += 1
        if self.fail_cleanup: raise OSError('cleanup failed')
        return {'started': self.started == 1, 'errors': []}
    def event_data(self):
        if self.fail_event_data: raise OSError('retained log read failed')
        events = [{'t': t, 'SUBSYSTEM': 'power_supply', 'POWER_SUPPLY_NAME': name,
                   'POWER_SUPPLY_ONLINE': value} for t, value in [(4, '0'), (7, '1')]
                  for name in ['samurai-usb-input', 'mp2650-input']]
        return {'battery_name': 'bq27541-0', 'kernel_events': events,
                'dbus_log': signal(1004.2, audit.DISPLAY, {'State': ('uint32', 2)})}
    def save(self, name, data): self.saved[name] = copy.deepcopy(data)


CONFIG = dict(execute=True, window_confirmed=True, transaction='charging-icon-test',
              max_seconds=80, output_root='/unused', boot_id='approved', manifest_sha256='approved')


class CandidateTests(unittest.TestCase):
    def run_capture(self, boundary=None, config=None):
        boundary = boundary or FakeIO()
        result = worker.run(config or CONFIG, boundary, audit.audit)
        return boundary, result

    def test_import_is_inert(self):
        with patch('pathlib.Path.read_text', side_effect=AssertionError('read on import')), \
             patch('subprocess.Popen', side_effect=AssertionError('spawn on import')):
            load('worker'); load('audit')

    def test_execute_and_window_required_before_any_io(self):
        for key in ['execute', 'window_confirmed']:
            boundary = FakeIO()
            with self.assertRaises(ValueError): self.run_capture(boundary, {**CONFIG, key: False})
            self.assertEqual(boundary.created, 0)

    def test_names_and_bounds_rejected(self):
        for edit in [{'transaction': '../old'}, {'max_seconds': 49}, {'max_seconds': 601}]:
            boundary = FakeIO()
            with self.assertRaises(ValueError): self.run_capture(boundary, {**CONFIG, **edit})
            self.assertEqual(boundary.created, 0)

    def test_fresh_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            boundary = worker.RealIO(); config = {**CONFIG, 'output_root': temp}
            boundary.create_new(config)
            marker = boundary.out / 'marker'; marker.write_text('keep')
            with self.assertRaises(FileExistsError): boundary.create_new(config)
            self.assertEqual(marker.read_text(), 'keep')

    def test_complete_cycle_ready_ticks_and_twenty_five_second_settle(self):
        boundary, result = self.run_capture()
        self.assertTrue(result['physical_cycle_passed'])
        self.assertFalse(result['screen_latency_verified'])
        self.assertEqual(boundary.statuses[2]['phase'], 'ready')
        self.assertTrue(boundary.statuses[2]['ready_for_user_action'])
        self.assertEqual(boundary.statuses[3]['tick'], 4)
        self.assertEqual(boundary.statuses[-1]['phase'], 'terminal')
        self.assertFalse(boundary.statuses[-1]['ready_for_user_action'])
        evidence = result['raw_cycle_evidence']
        self.assertEqual(evidence['offline_span'], 2)
        self.assertEqual(evidence['online_span'], 27)
        self.assertEqual(boundary.saved['capture-private.json']['duration_seconds'], 34)
        self.assertEqual(len(boundary.appended), 35)

    def test_current_negative_and_flags_preserved_no_charge_invention(self):
        boundary, result = self.run_capture()
        self.assertTrue(all(r['status'] == 'Discharging' and r['current_now_ua'] == -4000
                            for r in result['sample_status_current_sequence']))
        self.assertEqual(result['sample_status_current_sequence'][4]['telemetry_flags'], 0x108)
        self.assertFalse(result['sample_status_current_sequence'][4]['flags_fresh'])

    def test_timeout_before_later_human_action_is_no_cycle(self):
        boundary, result = self.run_capture(FakeIO(lambda t: sample(t)))
        self.assertFalse(result['physical_cycle_passed'])
        self.assertEqual(result['terminal_reason'], 'deadline')
        self.assertEqual(boundary.saved['capture-private.json']['duration_seconds'], 80)
        self.assertFalse(boundary.statuses[-1]['active'])

    def test_deadline_counts_sleep_time_without_starting_pm(self):
        class Boundary(FakeIO):
            def sleep(self, seconds):
                super().sleep(seconds); self.boot_extra += 100
        boundary, result = self.run_capture(Boundary())
        self.assertFalse(result['physical_cycle_passed'])
        self.assertEqual(result['sample_count'], 1)
        self.assertEqual(boundary.saved['capture-private.json']['elapsed_boottime_seconds'], 101)

    def test_configured_or_budget_zero_cannot_replace_physical_offline(self):
        def row(t):
            value = sample(t); value['udc_state'] = 'configured'
            value['telemetry']['budget_ua'] = 0 if 4 <= t <= 6 else 100000
            return value
        _, result = self.run_capture(FakeIO(row))
        self.assertFalse(result['physical_cycle_passed'])
        self.assertFalse(result['raw_cycle_evidence']['offline_confirmed'])

    def test_mixed_source_acok_and_short_detach_not_enough(self):
        for rows in [lambda t: sample(t, 0, 1) if 4 <= t <= 6 else sample(t),
                     lambda t: sample(t, 0, 0) if 4 <= t <= 5 else sample(t)]:
            _, result = self.run_capture(FakeIO(rows))
            self.assertFalse(result['physical_cycle_passed'])

    def test_short_online_period_not_complete(self):
        def rows(t): return sample(t, 0, 0) if 4 <= t <= 6 or t >= 20 else sample(t)
        _, result = self.run_capture(FakeIO(rows))
        self.assertFalse(result['physical_cycle_passed'])

    def test_raw_summary_cannot_forge_cycle(self):
        boundary, _ = self.run_capture(FakeIO(lambda t: sample(t)))
        raw = boundary.saved['capture-private.json']
        raw['terminal_reason'] = 'cycle_complete'
        raw['cycle'] = dict(offline_confirmed=True, settling_complete=True,
                            offline_samples=10, offline_span=10, online_samples=30, online_span=30)
        self.assertFalse(audit.audit(raw)['physical_cycle_passed'])

    def test_sparse_samples_not_continuous_offline(self):
        rows = [sample(t) for t in [0, 1, 2]] + [sample(t, 0, 0) for t in [3, 10, 20]]
        rows += [sample(t) for t in range(21, 52)]
        self.assertFalse(audit.physical_samples(rows)['offline_confirmed'])

    def test_gap_in_online_tail_restarts_settling(self):
        rows = [sample(t) if t < 4 or t > 6 else sample(t, 0, 0) for t in range(25)]
        rows += [sample(t) for t in range(40, 60)]
        self.assertFalse(audit.physical_samples(rows)['settling_complete'])

    def test_baseline_gap_revokes_ready_until_three_fresh_samples(self):
        cycle = worker.Cycle()
        for t in [0, 1, 2]: cycle.feed(sample(t))
        self.assertEqual(cycle.feed(sample(10)), 'sample_gap')
        self.assertIsNone(cycle.ready_at)
        self.assertEqual(cycle.feed(sample(11)), 'baseline')

    def test_baseline_health_failure_revokes_ready_and_mixed_edge_revokes_action_flag(self):
        cycle = worker.Cycle()
        for t in [0, 1, 2]: cycle.feed(sample(t))
        bad = sample(3); bad['telemetry']['error'] = -5
        self.assertEqual(cycle.feed(bad), 'baseline')
        self.assertIsNone(cycle.ready_at)
        for t in [4, 5, 6]: cycle.feed(sample(t))
        self.assertEqual(cycle.feed(sample(7, 0, 1)), 'awaiting_complete_offline')
        self.assertTrue(cycle.action_seen)

    def test_discovery_preflight_failure_still_terminal_and_raw(self):
        boundary = FakeIO(); boundary.fail_discovery = True
        boundary, result = self.run_capture(boundary)
        self.assertFalse(result['physical_cycle_passed'])
        self.assertEqual(boundary.started, 0)
        self.assertEqual(boundary.saved['capture-private.json']['exception']['type'], 'ValueError')
        self.assertTrue(boundary.statuses[-1]['terminal'])

    def test_wrong_identity_never_starts_monitors(self):
        boundary = FakeIO(); boundary.fail_identity = True
        _, result = self.run_capture(boundary)
        self.assertEqual(boundary.started, 0); self.assertEqual(boundary.discovered, 0)
        self.assertFalse(result['physical_cycle_passed'])

    def test_read_exception_and_monitor_death_keep_partial_raw_no_retry(self):
        for field in ['fail_sample', 'fail_alive']:
            boundary = FakeIO(); setattr(boundary, field, 5)
            _, result = self.run_capture(boundary)
            self.assertEqual(result['terminal_reason'], 'exception')
            self.assertEqual(len(boundary.saved['capture-private.json']['samples']), 5)
            self.assertEqual(boundary.started, 1); self.assertEqual(boundary.stopped, 1)
            self.assertFalse(result['physical_cycle_passed'])

    def test_cleanup_and_retained_log_errors_independent(self):
        for field in ['fail_cleanup', 'fail_event_data']:
            boundary = FakeIO(); setattr(boundary, field, True)
            _, result = self.run_capture(boundary)
            self.assertEqual(result['terminal_reason'], 'cycle_complete')
            self.assertFalse(result['physical_cycle_passed'])
            self.assertEqual(len(boundary.saved['capture-private.json']['samples']), 35)
            self.assertTrue(boundary.statuses[-1]['terminal'])

    def test_audit_error_keeps_capture_and_explicit_failure(self):
        boundary = FakeIO()
        def broken(raw): raise ValueError('injected audit failure')
        result = worker.run(CONFIG, boundary, broken)
        self.assertIn('capture-private.json', boundary.saved)
        self.assertFalse(result['physical_cycle_passed'])
        self.assertIn('audit_error', result)

    def test_missing_state_never_uses_update_time(self):
        boundary, _ = self.run_capture()
        raw = boundary.saved['capture-private.json']
        raw['dbus_log'] = signal(1004.2, audit.DISPLAY, {'UpdateTime': ('uint64', 1004)})
        result = audit.audit(raw); edge = result['edges'][0]
        self.assertEqual(edge['display_state_events'], [])
        self.assertIsNone(edge['source_to_first_following_display_state_event_seconds_estimated'])

    def test_endpoint_clock_discontinuity_suppresses_estimates(self):
        boundary, _ = self.run_capture(); raw = boundary.saved['capture-private.json']
        raw['clock_end']['real'] += 1
        result = audit.audit(raw)
        self.assertFalse(result['clock_mapping']['endpoints_consistent'])
        self.assertEqual(result['edges'][0]['display_state_events'], [])

    def test_real_state_event_maps_with_timing_scope(self):
        _, result = self.run_capture(); edge = result['edges'][0]
        self.assertEqual(edge['display_state_events'][0]['state'], 2)
        self.assertAlmostEqual(edge['source_to_first_following_display_state_event_seconds_estimated'], .2)

    def test_dbus_scalars_wrong_interface_nonfinite_bad_enum_and_truncation(self):
        text = signal(1004, audit.DISPLAY, {'State': ('uint32', 2), 'Percentage': ('double', 100),
                'Present': ('boolean', 'true'), 'NativePath': ('string', '"abc"')})
        signals, errors = audit.parse_dbus(text)
        self.assertFalse(errors); self.assertEqual(signals[0]['values']['NativePath'], 'abc')
        self.assertTrue(signals[0]['values']['Present'])
        self.assertFalse(audit.parse_dbus(signal(1004, audit.DISPLAY, {'State': ('uint32', 2)}, 'wrong'))[0])
        for values in [{'Percentage': ('double', 'nan')}, {'State': ('uint32', 99)}]:
            self.assertTrue(audit.parse_dbus(signal(1004, audit.DISPLAY, values))[1])
        self.assertTrue(audit.parse_dbus(text[:-8])[1])

    def test_partial_log_recovery_preserves_rows_never_qualifies_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'samples-private.jsonl').write_text(json.dumps(sample(0)) + '\n{cut')
            raw = audit.load_directory(path)
            self.assertEqual(len(raw['samples']), 1)
            self.assertEqual(len(raw['capture_errors']), 2)
            result = audit.audit(raw)
            self.assertFalse(result['physical_cycle_passed'])
            self.assertFalse(result['clock_mapping']['endpoints_consistent'])

    def test_real_sample_reads_only_standard_properties_and_cached_flags(self):
        boundary = worker.RealIO(); boundary.battery = Path('/fake/Battery')
        seen = []
        values = {'telemetry': 'valid=1 online=1 flags=49352 age_ms=100', 'online': 1,
                  'status': 'Discharging', 'current_now': -4000}
        def read(path, numeric=False):
            path = Path(path); seen.append(str(path)); return values[path.name]
        with patch.object(boundary, 'read', side_effect=read), \
             patch.object(worker.time, 'monotonic', side_effect=[100, 100.001]):
            row = boundary.sample(100)
        self.assertEqual(row['telemetry']['flags'], 49352)
        self.assertTrue(row['flags_fresh'])
        self.assertEqual(row['battery']['current_now_ua'], -4000)
        self.assertEqual([Path(p).name for p in seen], ['telemetry', 'online', 'online', 'status', 'current_now'])
        self.assertNotIn('register', ' '.join(seen).lower())

    def test_actual_telemetry_parse_error_retains_evidence(self):
        boundary = worker.RealIO(); boundary.battery = Path('/fake/Battery')
        with patch.object(boundary, 'read', return_value={'errno': 5}): row = boundary.sample(0)
        self.assertEqual(row['telemetry']['parse_error'], {'errno': 5})
        self.assertFalse(row['flags_fresh'])

    def test_partial_kernel_jsonl_does_not_discard_previous_events(self):
        with tempfile.TemporaryDirectory() as temp:
            boundary = worker.RealIO(); boundary.out = Path(temp)
            (boundary.out / 'kernel-events-private.jsonl').write_text('{"t": 1}\n{cut')
            events = boundary.event_data()
            self.assertEqual(events['kernel_events'], [{'t': 1}])
            self.assertEqual(len(events['event_read_errors']), 1)

    def test_netlink_real_receiver_keeps_only_power_supply_and_marks_truncation(self):
        events = object.__new__(worker.UIEvents)
        events.base = 100; events.errors = []; events.quit = threading.Event(); events.raw = io.StringIO()
        packets = [b'SUBSYSTEM=usb\0ACTION=change\0',
                   b'SUBSYSTEM=power_supply\0POWER_SUPPLY_NAME=mp2650-input\0POWER_SUPPLY_ONLINE=0\0']
        class Sock:
            def recvmsg(self, size):
                data = packets.pop(0)
                if not packets: events.quit.set()
                return data, [], worker.socket.MSG_TRUNC if not packets else 0, None
        events.sock = Sock()
        with patch.object(worker.time, 'monotonic', return_value=104): events.receive()
        lines = events.raw.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])['t'], 4)
        self.assertEqual(json.loads(lines[0])['POWER_SUPPLY_ONLINE'], '0')
        self.assertEqual(events.errors, ['truncated netlink packet'])

    def test_monitor_constructor_closes_owned_files_after_bind_failure(self):
        class Sock:
            closed = False
            def bind(self, address): raise OSError('bind failed')
            def close(self): self.closed = True
        sock = Sock()
        with tempfile.TemporaryDirectory() as temp, patch.object(worker.socket, 'socket', return_value=sock), \
             patch.object(worker.socket, 'AF_NETLINK', 16, create=True), \
             patch.object(worker.subprocess, 'Popen', side_effect=AssertionError('must not spawn')):
            with self.assertRaises(OSError): worker.UIEvents(Path(temp), 0)
            self.assertTrue(sock.closed)
            # Windows removal would fail if constructor retained these open handles.
            for path in Path(temp).iterdir(): path.unlink()

    def test_offline_cli_reads_only_retained_capture(self):
        boundary, _ = self.run_capture()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'capture-private.json'
            path.write_text(json.dumps(boundary.saved['capture-private.json']))
            before = path.read_bytes(); output = io.StringIO()
            with contextlib.redirect_stdout(output): audit.main(['--directory', temp])
            self.assertTrue(json.loads(output.getvalue())['physical_cycle_passed'])
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__': unittest.main(verbosity=2)
