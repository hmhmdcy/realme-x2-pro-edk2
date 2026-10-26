"""Retain the successful thread trace and the QEMU clone3 limitation as separate results."""
from pathlib import Path
import json
import host
HERE = Path(__file__).resolve().parent
report = json.loads((HERE / 'proxy-contract-validation.json').read_text())
assert report['results'][0]['mode'] == 'threaded' and report['results'][0]['exit_code'] == 0
assert b'AE_MODEL_PASS frames=720' in (host.PRIVATE / 'proxy-threaded-r1-private.log').read_bytes()
assert b'Failed to fork: Function not implemented' in (host.PRIVATE / 'proxy-isolated-r1-private.log').read_bytes()
report.update(threaded_passed=True, isolated_environment_limited=True, isolated_worker_started=False,
              actual_generated_proxy_and_worker=False, generated_threaded_proxy_exercised=True,
              full_isolated_ipc_verification_pending=True,
              prior_thread_harness_timeout_retained=True,
              failure_reason='QEMU user emulation does not implement SYS_clone3 used by libcamera Process')
(HERE / 'proxy-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
