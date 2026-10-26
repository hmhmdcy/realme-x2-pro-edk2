"""Freeze R2 only; retain R1 receipts and do not replay their cases."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'usb-irq-protection-stage-host-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    test = json.loads((HERE / 'test-result.json').read_bytes())
    assert test['passed'] and test['new_case_count'] == 3
    assert all(case['passed'] for case in test['new_cases'])
    assert test['default_source_only']['terminal'] and test['default_source_only']['returncode'] == 0
    for name, digest in test['files'].items():
        assert sha((HERE / name).read_bytes()) == digest
    assert sha((R1 / 'delivery.json').read_bytes()) == test['reused_R1_delivery_sha256'] == 'f126a56b680298f54313fb2a232f84462f8a218e8647fc3e706934f097221b17'
    assert sha((R1 / 'test-result.json').read_bytes()) == test['reused_R1_tests_sha256']
    assert sha((R1 / 'interface-check-result.json').read_bytes()) == test['reused_R1_interface_sha256']
    patch = ''.join(''.join(difflib.unified_diff((R1 / name).read_text().splitlines(True),
        (HERE / name).read_text().splitlines(True), fromfile='R1/' + name, tofile='R2/' + name))
        for name in ('host.py', 'remote.py'))
    (HERE / 'r1-to-r2.patch').write_text(patch)
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    files = ['host.py', 'remote.py', 'supervisor.py', 'pin-frozen-sources.py', 'source-pins.json',
             'test-r2.py', 'test-result.json', 'README.md', 'r1-to-r2.patch', 'freeze.py']
    result = dict(schema='samurai-usb-irq-protection-stage-host-delivery-r2', passed=True, frozen=True,
        files={name: dict(sha256=sha((HERE / name).read_bytes()), bytes=(HERE / name).stat().st_size) for name in files},
        worker_sha256=pins['worker']['sha256'], worker_delivery_sha256=pins['worker_delivery']['sha256'],
        supervisor_sha256=pins['supervisor']['sha256'], supervisor_byte_equal_R1=True,
        reused_R1_delivery_sha256=test['reused_R1_delivery_sha256'],
        reused_20_case_receipt_sha256=test['reused_R1_tests_sha256'],
        reused_interface_receipt_sha256=test['reused_R1_interface_sha256'],
        new_boundary_cases=3, old_20_or_interface_rerun=False,
        receipt_failure_before_send_closes_stdin_then_waits=True,
        partial_communicate_failure_closes_stdin_then_waits=True,
        truncated_parent_receipt_fetch_retains_raw_and_unknown=True,
        original_error_and_once_intent_retained=True,
        default_source_only_returncode=0, actual_runtime_request_or_identity_bound=False,
        device_or_transport_accessed=False, prepared_Image502_or_current_pointer_modified=False,
        stage_only_runtime_pending=True, reboot_or_carrier_write_supported=False)
    target = HERE / 'delivery.json'
    with target.open('xb') as output:
        output.write((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(dict(frozen=True, delivery_sha256=sha(target.read_bytes()),
                          host_sha256=sha((HERE / 'host.py').read_bytes()), remote_sha256=sha((HERE / 'remote.py').read_bytes()),
                          test_receipt_sha256=sha((HERE / 'test-result.json').read_bytes()))))


if __name__ == '__main__': main()
