"""Freeze local source/check receipts; never bind runtime identity or dispatch."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    test = json.loads((HERE / 'test-result.json').read_bytes())
    interface = json.loads((HERE / 'interface-check-result.json').read_bytes())
    assert test['passed'] and test['count'] == 20 and not test['actual_runtime_request_or_identity_generated']
    assert interface['passed'] and interface['interface_cases'] == 1
    assert interface['default_source_only_child']['terminal'] and interface['default_source_only_child']['returncode'] == 0
    for name, digest in test['source_files'].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    assert interface['host_sha256'] == sha((HERE / 'host.py').read_bytes())
    assert interface['source_sha256'] == sha((HERE / 'test-interface.py').read_bytes())
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    names = ['host.py', 'remote.py', 'supervisor.py', 'pin-frozen-sources.py', 'source-pins.json',
             'test-delta.py', 'test-result.json', 'test-interface.py', 'interface-check-result.json', 'README.md', 'freeze.py']
    delivery = dict(schema='samurai-usb-irq-protection-stage-host-delivery-v1', passed=True, frozen=True,
        files={name: dict(sha256=sha((HERE / name).read_bytes()), bytes=(HERE / name).stat().st_size) for name in names},
        worker_sha256=pins['worker']['sha256'], worker_delivery_sha256=pins['worker_delivery']['sha256'],
        worker_contract_sha256=pins['worker_contract']['sha256'],
        supervisor_sha256=pins['supervisor']['sha256'], actual_new_host_boundary_cases=20,
        actual_interface_cases=1, default_source_only_cli_returncode=0,
        actual_runtime_request_generated=False, actual_Image502_identity_bound=False,
        network_device_or_prepared_Image502_or_pointer_modified=False,
        launch_once_intent=True, worker_stdin_regular_request_fd=True,
        detached_supervisor_owns_and_waits_same_Popen=True,
        rebooted_source_only_fetch_no_current_PID_attribution=True,
        stage_success_is_only_runtime_pending=True, reboot_or_carrier_write_supported=False,
        old_suites_rerun=False)
    target = HERE / 'delivery.json'
    with target.open('xb') as output:
        output.write((json.dumps(delivery, indent=2) + '\n').encode())
    print(json.dumps(dict(frozen=True, delivery_sha256=sha(target.read_bytes()), worker_sha256=delivery['worker_sha256'],
                          supervisor_sha256=delivery['supervisor_sha256'])))


if __name__ == '__main__':
    main()
