#!/usr/bin/env python3
"""Exercise the actual GATT cleanup methods against local failure-injection objects."""
import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest import mock


def load(path, name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Harness:
    def __init__(self, module, output, failures=()):
        self.module = module
        self.failures = set(failures)
        self.calls = []
        self.timeouts = []
        self.connected = True
        self.adapter = dict(Powered=True, Pairable=False, Discoverable=False,
                            PairableTimeout=0, DiscoverableTimeout=180)
        args = SimpleNamespace(output=str(output), seconds=60, adapter='/org/bluez/hci0',
                               peer_address='02:11:22:33:44:55', storage='/not-read/keys', offline_export=False)
        self.run = module.PeerRun(args)
        self.original_log = self.run.events_file
        harness = self
        class EventLog:
            def write(self, data):
                harness.hit('event.write')
                return harness.original_log.write(data)
            def flush(self):
                harness.hit('event.flush')
                harness.original_log.flush()
            def close(self):
                harness.original_log.close()
                harness.hit('event.close')
        self.run.events_file = EventLog()
        self.owner = ':1.42'
        self.run.owner = self.owner
        self.identity = {'fixture-identity': True}
        self.keys = {'fixture-keys': True}
        self.run.identity_before = self.identity.copy()
        self.run.keys_before = self.keys.copy()
        self.run.original = dict(Powered=False, Pairable=False, Discoverable=False,
                                 PairableTimeout=0, DiscoverableTimeout=180)
        self.run.owned_adapter_mutations = ['Powered', 'Pairable', 'Discoverable']
        self.run.application_requested = self.run.advertisement_requested = True
        self.run.capture_backend = 'native-monitor'
        self.peer_path = '/org/bluez/hci0/dev_00_11_22_33_44_55'
        self.run.control = SimpleNamespace(call_blocking=self.owner_query, get_object=self.control_proxy,
                                           close=lambda: self.hit('control.close'))
        self.run.export = SimpleNamespace(get_object=self.export_proxy, close=lambda: self.hit('export.close'))
        self.run.advertisement = SimpleNamespace(remove_from_connection=lambda: self.hit('advertisement.remove'))
        objects = [SimpleNamespace(remove_from_connection=lambda i=i: self.hit('gatt.remove.' + str(i)))
                   for i in range(3)]
        app = SimpleNamespace(objects=objects, remove_from_connection=lambda: self.hit('application.remove'))
        app.remove_all = lambda: module.Application.remove_all(app)
        self.run.app = app
        self.run.native_capture = SimpleNamespace(close=lambda: self.hit('native.close'),
            thread=SimpleNamespace(is_alive=lambda: False), packet_count=4, error=None)
        self.run.loop = SimpleNamespace(quit=lambda: self.hit('loop.quit'))

    def hit(self, label):
        self.calls.append(label)
        if label in self.failures:
            raise OSError('injected-' + label)

    def bounded(self, kwargs):
        timeout = kwargs['timeout']
        assert 0 < timeout <= 3
        self.timeouts.append(timeout)

    def owner_query(self, *args, **kwargs):
        self.bounded(kwargs)
        assert args[:4] == ('org.freedesktop.DBus', '/org/freedesktop/DBus',
                            'org.freedesktop.DBus', 'GetNameOwner')
        self.hit('owner.query')
        return ':1.99' if 'owner.replaced' in self.failures else self.owner

    def export_proxy(self, owner, path, introspect):
        assert owner == self.owner and path == self.run.args.adapter and introspect is False
        self.hit('export.proxy')
        def unregister(label, value, **kwargs):
            self.bounded(kwargs)
            self.hit(label)
        return SimpleNamespace(UnregisterAdvertisement=lambda value, **kw: unregister('unregister.advertisement', value, **kw),
                               UnregisterApplication=lambda value, **kw: unregister('unregister.application', value, **kw))

    def control_proxy(self, owner, path, introspect):
        assert owner == self.owner and introspect is False
        if path == '/':
            def managed(**kwargs):
                self.bounded(kwargs)
                self.hit('managed.read')
                return {self.peer_path: {self.module.DEVICE_IFACE: {
                    'Address': self.run.args.peer_address, 'Connected': self.connected}}}
            return SimpleNamespace(GetManagedObjects=managed)
        if path == self.peer_path:
            def disconnect(**kwargs):
                self.bounded(kwargs)
                self.hit('peer.disconnect')
                self.connected = False
            return SimpleNamespace(Disconnect=disconnect)
        assert path == self.run.args.adapter
        def setter(interface, name, value, **kwargs):
            self.bounded(kwargs)
            assert interface == self.module.ADAPTER_IFACE and value.variant_level == 1
            self.hit('adapter.set.' + name)
            self.adapter[name] = bool(value)
        def get_all(interface, **kwargs):
            self.bounded(kwargs)
            self.hit('adapter.read.' + interface)
            return {'ActiveInstances': 0} if interface == self.module.ADV_MANAGER else self.adapter.copy()
        return SimpleNamespace(Set=setter, GetAll=get_all)

    def invoke(self, use_run=False):
        original_write = Path.write_text
        def write(path, *args, **kwargs):
            if path.name == 'summary-private.json':
                self.hit('summary.write')
            return original_write(path, *args, **kwargs)
        sink = io.StringIO()
        if 'stdout.write' in self.failures:
            class BrokenStdout(io.StringIO):
                def write(self, data):
                    raise OSError('injected-stdout.write')
            sink = BrokenStdout()
        with mock.patch.object(self.module, 'key_fingerprint', return_value=self.keys.copy()), \
             mock.patch.object(self.module, 'runtime_identity', return_value=self.identity.copy()), \
             mock.patch.object(Path, 'write_text', write), contextlib.redirect_stdout(sink):
            if use_run:
                self.run.prepare = lambda: setattr(self.run, 'stopping', True)
                with mock.patch.object(self.module.GLib, 'timeout_add', return_value=1), \
                     mock.patch.object(self.module.GLibUnix, 'signal_add', return_value=2):
                    self.run.run()
            else:
                self.run.stop('offline-fixture')
        assert self.run.cleanup_complete and not self.run.cleanup_in_progress
        assert self.run.stopping and not self.run.accepting
        for label in ('advertisement.remove', 'application.remove', 'export.close',
                      'control.close', 'event.close', 'loop.quit', 'summary.write'):
            assert label in self.calls, (label, self.calls)
        assert ('btmon.poll' if self.run.capture else 'native.close') in self.calls
        before_calls = list(self.calls)
        assert self.run.stop('second-stop') is False
        assert self.calls == before_calls, 'Repeated stop must not retry completed actions'

    def use_btmon(self):
        harness = self
        class Process:
            returncode = None
            def poll(self):
                harness.hit('btmon.poll')
                return self.returncode
            def send_signal(self, sig):
                assert sig == harness.module.signal.SIGINT
                harness.hit('btmon.signal')
            def wait(self, timeout):
                assert timeout in (2, 3)
                harness.hit('btmon.wait' if timeout == 3 else 'btmon.reap')
                if timeout == 3 and 'btmon.wait_timeout' in harness.failures:
                    raise harness.module.subprocess.TimeoutExpired('owned-fixture', timeout)
                if self.returncode is None:
                    self.returncode = 0
                return self.returncode
            def kill(self):
                harness.hit('btmon.kill')
                self.returncode = -9
        self.run.native_capture = None
        self.run.capture_backend = 'btmon'
        self.run.capture = Process()
        self.run.capture_log = SimpleNamespace(close=lambda: self.hit('capture_log.close'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New private directory')
    parser.add_argument('--before-source', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    server = Path(__file__).resolve().parents[2] / 'bluetooth-le-peer-20261023/phone-gatt-peer.py'
    ast.parse(server.read_text())
    current = load(server, 'cleanup_current')
    before_sha = hashlib.sha256(args.before_source.read_bytes()).hexdigest()
    assert before_sha == '096d01f85bac9900ab5be3b9b2ad773070b0c7d2d68348344ae321112f8694ff'
    before = load(args.before_source, 'cleanup_before')
    regression = Harness(before, args.output / 'old-regression', ('event.write',))
    try:
        regression.run.stop('old-log-failure')
        raise AssertionError('Old cleanup should reproduce the logging failure')
    except OSError:
        assert regression.run.stopping and 'native.close' not in regression.calls and 'loop.quit' not in regression.calls
    finally:
        regression.original_log.close()
    results = [{'case': 'old_096d_logging_failure_reproduced', 'passed': True}]
    cases = [
        ('normal', ()), ('log_write', ('event.write',)), ('log_flush', ('event.flush',)),
        ('summary_write', ('summary.write',)), ('owner_exception', ('owner.query',)),
        ('owner_replaced', ('owner.replaced',)), ('registration_proxy', ('export.proxy',)),
        ('unregister_advertisement', ('unregister.advertisement',)),
        ('disconnect_failure', ('peer.disconnect',)), ('restore_one_property', ('adapter.set.Discoverable',)),
        ('application_child_remove', ('gatt.remove.1',)), ('private_bus_close', ('export.close',)),
        ('native_capture_close', ('native.close',)), ('control_bus_close', ('control.close',)),
        ('events_close', ('event.close',)), ('loop_quit', ('loop.quit',)), ('stdout_write', ('stdout.write',)),
        ('combined_logs_summary_close', ('event.write', 'summary.write', 'export.close', 'native.close', 'control.close')),
        ('btmon_normal', ()), ('btmon_signal_error', ('btmon.signal',)),
        ('btmon_wait_timeout', ('btmon.wait_timeout',)), ('btmon_poll_error', ('btmon.poll',)),
        ('btmon_log_close_error', ('capture_log.close',)),
        ('stopping_is_not_complete', ()), ('run_finally_after_partial_stop', ())]
    for name, failures in cases:
        harness = Harness(current, args.output / name, failures)
        if name.startswith('btmon_'):
            harness.use_btmon()
        if name == 'stopping_is_not_complete':
            harness.run.stopping = True
        started = time.monotonic()
        harness.invoke(use_run=name == 'run_finally_after_partial_stop')
        assert harness.run.cleanup_deadline <= started + 30.01
        assert time.monotonic() - started < 3, 'Mocks must not sleep out real cleanup budgets'
        if name.startswith('owner_'):
            assert not any(s.startswith(('unregister.', 'adapter.set.')) or s == 'peer.disconnect' for s in harness.calls)
            assert harness.run.cleanup_report['cleanup']['adapter_restored'] is False
        else:
            for action in ('unregister.advertisement', 'unregister.application', 'peer.disconnect',
                           'adapter.set.Discoverable', 'adapter.set.Pairable', 'adapter.set.Powered'):
                if name != 'registration_proxy' or not action.startswith('unregister.'):
                    assert action in harness.calls, (name, action, harness.calls)
        assert harness.run.exit_code == (1 if failures else 0), (name, harness.run.errors)
        if name.startswith('btmon_'):
            assert harness.run.capture.returncode is not None and 'capture_log.close' in harness.calls
            if name in ('btmon_signal_error', 'btmon_wait_timeout'):
                assert 'btmon.kill' in harness.calls and 'btmon.reap' in harness.calls
        if failures:
            assert harness.run.errors
        else:
            assert not harness.run.errors
        results.append(dict(case=name, passed=True, errors_recorded=len(harness.run.errors),
                            all_local_finalizers_attempted=True, exit_code=harness.run.exit_code))

    reentrant = Harness(current, args.output / 'reentrant')
    reentrant.run.advertisement.remove_from_connection = lambda: (
        reentrant.hit('advertisement.remove'), reentrant.run.stop('nested-stop'))
    reentrant.invoke()
    assert reentrant.calls.count('unregister.application') == 1 and reentrant.calls.count('native.close') == 1
    results.append(dict(case='nested_stop_does_not_reenter_or_duplicate_cleanup', passed=True))

    expired = Harness(current, args.output / 'expired-budget')
    expired.run.cleanup_deadline = time.monotonic() - 1
    original_deadline = expired.run.cleanup_deadline
    expired.invoke()
    assert expired.run.cleanup_deadline == original_deadline and not expired.timeouts
    assert expired.run.exit_code == 1 and 'native.close' in expired.calls and 'loop.quit' in expired.calls
    results.append(dict(case='expired_shared_budget_still_closes_local_resources_without_state_calls', passed=True))

    capture_calls = []
    native = current.NativeMonitorCapture.__new__(current.NativeMonitorCapture)
    native.stop_event = threading.Event()
    native.monitor = SimpleNamespace(close=lambda: (_ for _ in ()).throw(OSError('socket-close-fault')))
    native.thread = SimpleNamespace(ident=1, join=lambda **kw: capture_calls.append(kw['timeout']), is_alive=lambda: False)
    native.log = None
    try:
        native.close()
        raise AssertionError('Expected preserved socket close error')
    except RuntimeError as error:
        assert 'socket-close-fault' in str(error) and capture_calls == [1] and native.stop_event.is_set()
    results.append(dict(case='actual_native_close_still_joins_after_socket_close_error', passed=True))

    report = dict(passed=True, case_count=len(results), results=results,
                  before_server_sha256=before_sha, server_sha256=hashlib.sha256(server.read_bytes()).hexdigest(),
                  actual_PeerRun_stop_run_cleanup_call_and_native_close_executed=True,
                  only_local_mock_objects_and_private_files=True, private_or_system_DBus_connected=False,
                  HCI_socket_opened=False, phone_SSH_WinRT_or_SDK_accessed=False,
                  prior_hardware_and_protocol_reports_rewritten=False)
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
