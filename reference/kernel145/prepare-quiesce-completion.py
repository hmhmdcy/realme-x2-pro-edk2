"""Bind a transition-only exception to the already sealed140 shutdown, never a fresh stop."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
target = out / 'observed-shutdown-expected-private.json'
assert not target.exists()
with tarfile.open(out / 'quiesce-failure-private.tar.gz') as archive:
    data = {}
    for member in archive:
        assert not member.issym() and not member.islnk()
        if member.isfile():
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts and member.name not in data
            data[member.name] = archive.extractfile(member).read()
prefix = 'k145-quiesce-failure-audit/'
for line in data[prefix + 'SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[prefix + name.removeprefix('./')]).hexdigest() == digest
before = data['k145-quiesce/dmesg-before.txt']
after = data[prefix + 'dmesg-current-private.txt']
assert after.startswith(before)
delta = after[len(before):].decode()
failed = [line for line in delta.splitlines() if 'unable to prepare channel' in line]
assert len(failed) == 70
assert all(re.fullmatch(r'\[\s*\d+\.\d+\] qcom,slim-ngd-ctrl 171c0000.slim-ngd: unable to prepare channel', line) for line in failed)
assert not re.search(r'WARNING:|BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|frame done timeout|dsi_err_worker|Unable to allocate TID|TX queue full|BAM.*allocation failed', delta)
assert data[prefix + 'state.txt'].splitlines()[-1] == b'0'
assert data[prefix + 'boot-id-private.txt'] == (out / 'source-boot-id-private.txt').read_bytes()
assert b'#140 SMP' in data[prefix + 'uname.txt']
assert data[prefix + 'remoteprocs.txt'].splitlines() == [b'0 slpi offline', b'1 modem offline', b'2 adsp offline']
assert not data[prefix + 'phosh.txt'].strip() and not data[prefix + 'phoc.txt'].strip()
assert b'active=1' not in data[prefix + 'drm-private.txt']
assert len(data[prefix + 'drm-clients-private.txt'].splitlines()) == 1
assert data[prefix + 'amps.txt'].count(b'powered=0 muted=1') == 2
assert b'failed=1' not in data[prefix + 'amps.txt']
assert data[prefix + 'soundcards.txt'].strip() == b'--- no soundcards ---'
assert data[prefix + 'sensors.txt'].strip() == b'vdd=0 vddio=0'
assert data[prefix + 'traces.txt'].splitlines() == [b'0', b'0']
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1), ('partition-check.txt', 3), ('new-module-check.txt', 784)]:
    assert data['k145-quiesce/' + name].count(b': OK') == count
    assert b'FAILED' not in data['k145-quiesce/' + name]
expected = dict(stage=145, current_kernel=140, target_kernel=145,
                boot_id=data[prefix + 'boot-id-private.txt'].decode().strip(),
                before_sha256=hashlib.sha256(before).hexdigest(),
                sealed_after_sha256=hashlib.sha256(after).hexdigest(),
                sealed_after_bytes=len(after), shutdown_tx_prepare_failures=70,
                taint=0, transition_only=True, each_failure_channel_state_not_recorded=True,
                old_shutdown_fault_not_fixed=True, runtime_accepted=False, goal_complete=False)
target.write_text(json.dumps(expected, indent=2) + '\n')
backup = out / 'quiesce-tools-before-seal-private'
assert not backup.exists()
backup.mkdir()
for name in ['check-quiesce-state.py', 'verify-quiesce.py']:
    shutil.copyfile(ref / name, backup / name)
report = {key: value for key, value in expected.items() if key not in ['boot_id', 'before_sha256', 'sealed_after_sha256', 'sealed_after_bytes']}
report.update(sealed_failure_archive_verified=True, fully_quiesced_and_protected_checks_pass=True,
              shutdown_not_replayed=True, new_candidate_not_deployed=True,
              comparison_with143_does_not_prove_every_failure_null_down=True)
(ref / 'observed-shutdown-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_EXACT_SEALED140_SHUTDOWN70_BOUND_TRANSITION_ONLY_NOT_A_FIX')
