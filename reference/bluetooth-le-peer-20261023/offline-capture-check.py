#!/usr/bin/env python3
"""Exercise monitor capture lifetime with AF_UNIX fixtures only; no HCI/system bus."""
import argparse
import ast
import contextlib
import ctypes
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import struct
import sys
import threading
import time
from types import SimpleNamespace
from unittest import mock


def wait_for(predicate):
    deadline = time.monotonic() + 2
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError('Offline fixture deadline')
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New private directory; parent must exist')
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    server = Path(__file__).with_name('phone-gatt-peer.py')
    sys.dont_write_bytecode = True
    tree = ast.parse(server.read_text())
    spec = importlib.util.spec_from_file_location('capture_fixture', server)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = []
    capture_nodes = [node for node in tree.body if getattr(node, 'name', '') in
                     ('open_native_monitor', 'NativeMonitorCapture')]
    assert len(capture_nodes) == 2
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in ('send', 'sendto', 'sendmsg')
                   for parent in capture_nodes for node in ast.walk(parent))
    checks.append('Delivered server parses; native monitor code has no socket send calls')

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    capture = None
    try:
        capture = module.NativeMonitorCapture(args.output / 'synthetic-monitor.jsonl', socket_factory=lambda: left)
        packet = struct.pack('<HHH', 3, 0, 5) + b'TEST!'
        right.send(packet)  # AF_UNIX fixture only, never an HCI or MGMT socket.
        wait_for(lambda: capture.packet_count == 1)
        assert capture.healthy()
        started = time.monotonic()
        capture.close()
        assert time.monotonic() - started < 1.25
        assert not capture.thread.is_alive() and left.fileno() == -1 and capture.log.closed
        record = json.loads((args.output / 'synthetic-monitor.jsonl').read_text())
        assert set(record) == {'monotonic', 'packet'} and record['packet'] == packet.hex()
        checks.append('AF_UNIX frame preserved in kernel185 monotonic+packet.hex JSONL; FD/thread/log close bounded')
    finally:
        if capture:
            capture.close()
        right.close()
        left.close()

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    capture = module.NativeMonitorCapture(args.output / 'idle-monitor.jsonl', socket_factory=lambda: left)
    try:
        capture.close()
        assert not capture.thread.is_alive() and left.fileno() == -1 and capture.log.closed
        assert capture.error is None
        checks.append('Idle receive timeout permits clean bounded shutdown without a fabricated packet')
    finally:
        capture.close()
        right.close()

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        try:
            module.NativeMonitorCapture(args.output / 'missing-parent' / 'fail.jsonl', socket_factory=lambda: left)
            raise AssertionError('Expected output-open failure')
        except FileNotFoundError:
            assert left.fileno() == -1
        checks.append('Output-open failure closes the already-open fixture FD before registration could occur')
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    def fail_bind(fd, address, size):
        assert fd == left.fileno()
        assert (address._obj.family, address._obj.index, address._obj.channel) == (31, 0xffff, 2)
        ctypes.set_errno(13)
        return -1
    try:
        with mock.patch.object(module.socket, 'socket', return_value=left) as create, \
                mock.patch.object(module.ctypes, 'CDLL', return_value=SimpleNamespace(bind=fail_bind)):
            try:
                module.open_native_monitor()
                raise AssertionError('Expected bind failure')
            except PermissionError:
                pass
            create.assert_called_once_with(31, socket.SOCK_RAW | socket.SOCK_CLOEXEC, 1)
            assert left.fileno() == -1
        checks.append('Mocked channel2 bind failure preserves errno and closes FD; no HCI socket was created')
    finally:
        left.close()
        right.close()

    class BrokenReceiver:
        def __init__(self):
            self.fail = threading.Event()
            self.closed = False
        def settimeout(self, value):
            assert value == 0.25
        def recv(self, length):
            if self.fail.wait(timeout=0.02):
                raise OSError('synthetic-receive-failure')
            raise TimeoutError()
        def close(self):
            self.closed = True
    receiver = BrokenReceiver()
    capture = module.NativeMonitorCapture(args.output / 'failed-monitor.jsonl', socket_factory=lambda: receiver)
    try:
        receiver.fail.set()
        wait_for(lambda: not capture.healthy())
        assert 'synthetic-receive-failure' in capture.error
        stopped = []
        fake = SimpleNamespace(stopping=False, capture_backend='native-monitor', native_capture=capture,
                               capture=None, errors=[], stop=lambda reason: stopped.append(reason))
        fake.require_capture = lambda: module.PeerRun.require_capture(fake)
        assert module.PeerRun.capture_health(fake) is False
        assert stopped == ['capture-exited'] and fake.errors
        fake.proxy = lambda path: (_ for _ in ()).throw(AssertionError('Adapter mutation must not be reached'))
        try:
            module.PeerRun.set_adapter(fake, 'Powered', True, 1)
            raise AssertionError('Failed capture must block adapter mutation')
        except RuntimeError:
            pass
        fake.accepting = True
        fake.deadline = time.monotonic() + 5
        fake.args = SimpleNamespace(offline_export=False)
        with mock.patch.object(module.GLib, 'idle_add', side_effect=lambda function, *items: function(*items)):
            try:
                module.PeerRun.authorize(fake, {})
                raise AssertionError('Failed capture must block data access')
            except module.NotPermitted:
                pass
        assert stopped == ['capture-exited', 'capture-exited']
        capture.close()
        assert receiver.closed and not capture.thread.is_alive() and capture.log.closed
        checks.append('Injected reader failure is retained, stops health/data access, prevents adapter mutation, and closes cleanly')
    finally:
        capture.close()

    calls = []
    class NoIORun:
        def __init__(self, parsed):
            calls.append(parsed)
        def run(self):
            return 0
    module.PeerRun = NoIORun
    module.dbus.mainloop.glib.DBusGMainLoop = lambda **kwargs: None
    argv_before = sys.argv
    try:
        base = ['--output', '/not-created/fixture', '--peer-address', '02:11:22:33:44:55',
                '--boot-guard-file', '/not-read/guard', '--charging-manifest-sha256', '0' * 64]
        with contextlib.redirect_stderr(io.StringIO()):
            sys.argv = [str(server)] + base + ['--capture-backend', 'native-monitor']
            assert module.main() == 0 and calls[-1].capture_backend == 'native-monitor'
            sys.argv = [str(server), '--output', '/not-created/fixture', '--offline-export',
                        '--bus-address', 'unix:path=/not-opened', '--capture-backend', 'native-monitor']
            try:
                module.main()
                raise AssertionError('Offline export must reject runtime capture arguments')
            except SystemExit as error:
                assert error.code == 2
        checks.append('Explicit native backend parses only through a fake no-I/O runtime; offline-export rejects it')
    finally:
        sys.argv = argv_before

    report = {'capture_lifecycle_checks_passed': True, 'checks': checks, 'check_count': len(checks),
              'server_sha256': hashlib.sha256(server.read_bytes()).hexdigest(),
              'transport_used_for_packets': 'AF_UNIX socketpair and injected receiver only',
              'real_hci_socket_opened': False, 'system_bus_or_phone_accessed': False,
              'native_monitor_hardware_validated': False, 'btmon_runtime_validated': False,
              'prior_nine_DBus_checks_reused_without_rerun': True,
              'reused_implementation_sources': ['../kernel130/bt_mgmt.py:open_channel(2)',
                                                 '../kernel185/test-bluez-scan-preserve-pairs.py:record_hci']}
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
