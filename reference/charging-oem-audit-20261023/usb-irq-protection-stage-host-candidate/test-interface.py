"""One in-memory host->actual worker schema check and source-only CLI receipt."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    host = module('stage_host_interface', HERE / 'host.py')
    pins, raw = host.source_check()
    worker = module('frozen_stage_worker_interface', host.local(pins['worker']['path']))
    d = dict(boot='12345678-1234-4123-8123-123456789abc', serial_sha256='1' * 64,
             compatible_sha256='2' * 64, rootfs='3' * 64, postboot_raw_sha256='4' * 64)
    request = host.make_request('usb-irq-protection-stage-schema-test', d, pins['worker']['sha256'], raw['cohort_payload'])
    files, manifest = worker.unpack(request)
    assert len(files) == 3 and manifest['adapter_revision'] == 'usb-irq-protection-observer-01'
    lease = dict(transaction_id=request['transaction_id'], boot_id=d['boot'], token=request['lease_token'],
                 owner='charging', exclusive=True, camera_released=True, bluetooth_released=True,
                 issued_boottime_s=100.0, expires_boottime_s=220.0)
    worker.validate_lease(lease, 0o600, request, 100.0)
    started = time.monotonic()
    child = subprocess.Popen([sys.executable, '-B', str(HERE / 'host.py')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate()
    rc = child.wait()
    assert rc == 0 and not stderr
    assert json.loads(stdout) == dict(source_checks_passed=True, device_accessed=False, runtime_request_generated=False)
    result = dict(passed=True, interface_cases=1, actual_functions=['host.make_request', 'worker.unpack', 'worker.validate_lease'],
                  worker_sha256=pins['worker']['sha256'], host_sha256=sha((HERE / 'host.py').read_bytes()),
                  source_sha256=sha(Path(__file__).read_bytes()), actual_identity_and_clock=False,
                  synthetic_request_in_memory_only=True, actual_runtime_request_created=False,
                  default_source_only_child=dict(pid=child.pid, terminal=True, returncode=rc,
                      seconds=time.monotonic() - started, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)),
                  device_or_transport_accessed=False, old_suites_rerun=False)
    (HERE / 'interface-check-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, interface_cases=1, source_only_cli_returncode=rc)))


if __name__ == '__main__':
    main()
