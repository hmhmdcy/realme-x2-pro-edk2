#!/usr/bin/env python3
"""Offline scheduling checks only: no host import, SSH, WinRT, BlueZ or radio."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

path = Path(__file__).with_name('run-gatt-window.py')
spec = importlib.util.spec_from_file_location('coordinated_window', path)
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)


def case(ready=None, ready_error=False, client_error=False, server_error=False):
    reached = threading.Event()
    release = threading.Event()
    records = []

    def server():
        records.append('server_started')
        reached.set()
        assert release.wait(2)
        records.append('server_ended')
        if server_error:
            raise RuntimeError('fixture server error')
        return 0

    def readiness():
        assert reached.wait(2)
        records.append('readiness')
        if ready_error:
            release.set()
            raise RuntimeError('fixture readiness error')
        if not window.eligible(ready, 0):
            release.set()
        return ready

    def client():
        records.append('client_started_before_server_ended')
        assert not release.is_set()
        release.set()
        if client_error:
            raise RuntimeError('fixture client error')
        return 0

    report = window.coordinate(server, readiness, client)
    assert records[-1] == 'server_ended'
    assert report['server_terminal'] is not server_error
    return report, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    ready = dict(registered=True, stopping=False, finished=False, remaining_seconds=58)
    cases = {}
    report, records = case(ready)
    assert report['windows_client_started'] and report['client_exit'] == 0
    assert records == ['server_started', 'readiness', 'client_started_before_server_ended', 'server_ended']
    cases['ready_starts_client_in_same_process_before_awaiting_server'] = True
    report, _ = case(dict(ready, remaining_seconds=17.83))
    assert not report['windows_client_started']
    cases['insufficient_window_does_not_start_client'] = True
    report, _ = case(dict(ready, finished=True))
    assert not report['windows_client_started']
    cases['terminal_server_does_not_start_client'] = True
    report, _ = case(ready_error=True)
    assert not report['windows_client_started'] and report['orchestration_error_type'] == 'RuntimeError'
    cases['readiness_failure_still_awaits_owned_server'] = True
    report, _ = case(ready, client_error=True)
    assert report['windows_client_started'] and report['orchestration_error_type'] == 'RuntimeError'
    cases['client_failure_still_awaits_owned_server'] = True
    report, _ = case(dict(ready, finished=True), server_error=True)
    assert not report['server_terminal'] and report['server_transport_error_type'] == 'RuntimeError'
    cases['server_transport_failure_does_not_claim_native_terminal'] = True
    assert not window.eligible(ready, 16) and not window.eligible(dict(ready, stopping=True), 0)
    cases['host_monotonic_budget_and_stopping_gate_override_remote_claim'] = True
    result = dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), cases=cases,
                  all_passed=all(cases.values()), simulated_callbacks_only=True,
                  ssh_bluez_winrt_or_radio_accessed=False, real_hardware_orchestration_passed=False)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
