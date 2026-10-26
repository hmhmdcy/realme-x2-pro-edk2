"""Freeze pure stage-proof only; no whole-host or future activation material."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    test = json.loads((HERE / 'stage-test-result.json').read_bytes())
    assert test['passed'] and test['count'] == 13
    for name, digest in test['files'].items():
        assert sha((HERE / name).read_bytes()) == digest
    child = subprocess.Popen([sys.executable, '-B', str(HERE / 'stage-proof.py')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(); rc = child.wait()
    assert rc == 0 and not stderr
    assert json.loads(stdout) == dict(source_only=True, source_stage_reviewed=False, request_or_guard_created=False, device_accessed=False)
    names = ['stage-proof.py', 'stage-source-pins.json', 'pin-stage-sources.py', 'test-stage-proof.py',
             'stage-test-result.json', 'STAGE-PROOF.md', 'freeze-stage-proof.py']
    result = dict(schema='samurai-stage-proof-frozen-v1', passed=True,
        stage_proof_sha256=sha((HERE / 'stage-proof.py').read_bytes()),
        files={name: dict(sha256=sha((HERE / name).read_bytes()), bytes=(HERE / name).stat().st_size) for name in names},
        API=['review_stage(stage_directory, fetch_directory, *, expected_transaction=None)', 'guard_stage_fields(review)'],
        new_actual_boundary_cases=13, old_suites_rerun=False,
        default_source_only=dict(pid=child.pid, terminal=True, returncode=rc, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)),
        actual_stage_or_activation_or_postboot_request_created=False, device_or_transport_accessed=False,
        activation_operator_or_postboot_host_dependency=False)
    target = HERE / 'stage-proof-frozen.json'
    with target.open('xb') as output:
        output.write((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(dict(passed=True, stage_proof_sha256=result['stage_proof_sha256'], frozen_receipt_sha256=sha(target.read_bytes()))))


if __name__ == '__main__': main()
