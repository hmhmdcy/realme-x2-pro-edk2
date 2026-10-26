from pathlib import Path
import hashlib
import json
import tarfile
import host

archive = host.PRIVATE / 'k184-before-reboot-private.tar.gz'
expected = json.loads((host.PRIVATE / 'pre-reboot-archive-validation.json').read_text())['archive_sha256']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
folder = host.PRIVATE / 'before-reboot-evidence-private'
with tarfile.open(archive) as tar:
    tar.extractall(folder, filter='data')
ref = Path(__file__).resolve().parent
build = folder / 'k184-libssc-r2'
patch = (build / 'libssc-wise-light.patch').read_bytes()
report = json.loads((build / 'build-validation.json').read_text())
assert hashlib.sha256(patch).hexdigest() == report['patch_sha256']
assert hashlib.sha256((build / 'build-r4/src/libssc.so.2').read_bytes()).hexdigest() == report['candidate_sha256']
(ref / 'libssc-wise-light.patch').write_bytes(patch)
(ref / 'libssc-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
failed = folder / 'k184-sensor-light-v2'
assert (failed / 'result.txt').read_text().strip() == 'QUERY_NOT_RUN_START_FAILED'
failure = {'kernel_build': 183, 'same_boot_second_slpi_start_failed': True,
           'start_exit': int((failed / 'start-exit.txt').read_text()),
           'userspace_candidate_test_started': False, 'error': 'SLPI ready handshake timeout (-110)',
           'slpi_final': (failed / 'slpi-final-state.txt').read_text().strip(),
           'power_final': (failed / 'power-final.txt').read_text().strip(),
           'taint': int((failed / 'kernel-state-after.txt').read_text().splitlines()[-1]),
           'root_cause_proven': False, 'reboot_required_for_next_control': True}
(ref / 'slpi-restart-failure-validation.json').write_text(json.dumps(failure, indent=2) + '\n')
print(json.dumps({'library_and_patch_sha_verified': True, 'slpi_second_start_failure_preserved': True}))
