from pathlib import Path
import hashlib
import json
import re
import tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
with tarfile.open(out / 'quiesce-private.tar') as archive:
    data = {}
    for member in archive:
        assert not member.issym() and not member.islnk()
        if member.isfile():
            name = member.name.removeprefix('./')
            assert '..' not in Path(name).parts and not Path(name).is_absolute() and name not in data
            data[name] = archive.extractfile(member).read()
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'source-boot-id-private.txt').read_bytes()
assert len(data['drm-clients-after-gui.txt'].splitlines()) == 1
assert b'active=1' not in data['drm-final-state.txt'] and b'active=0' in data['drm-final-state.txt']
assert data['pcm-idle.txt'].strip() == b'closed\nclosed'
assert data['amps-final.txt'].count(b'powered=0 muted=1') == 2 and b'failed=1' not in data['amps-final.txt']
assert data['soundcards-after-stop.txt'].strip() == b'--- no soundcards ---'
assert data['remoteproc-final-state.txt'].splitlines() == [b'0 slpi offline', b'1 modem offline', b'2 adsp offline']
assert data['sensor-power-final-state.txt'].strip() == b'vdd=0 vddio=0'
state = json.loads(data['shutdown-state-validation.json'])
assert state['shutdown_state_validated'] and state['current_kernel'] == 140 and state['target_kernel'] == 145
taint = int(data['state.txt'].splitlines()[-1])
assert taint == state['taint'] and taint in (0, 512)
before, after = (data[name].decode() for name in ['dmesg-before.txt', 'dmesg-after.txt'])
assert after.startswith(before) and before.count('WARNING:') == 0
delta = after[len(before):]
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|frame done timeout|dsi_err_worker|Unable to allocate TID|TX queue full|BAM.*allocation failed', delta)
failed = [line for line in delta.splitlines() if 'unable to prepare channel' in line]
if failed:
    expected = json.loads((out / 'observed-shutdown-expected-private.json').read_text())
    assert expected == json.loads(data['observed-shutdown-expected-private.json'])
    assert expected['boot_id'] == data['boot-id-private.txt'].decode().strip()
    assert hashlib.sha256(before.encode()).hexdigest() == expected['before_sha256']
    assert hashlib.sha256(after.encode()[:expected['sealed_after_bytes']]).hexdigest() == expected['sealed_after_sha256']
    assert len(failed) == state['shutdown_tx_prepare_failures'] == 70
    assert state['sealed_shutdown_faults_transition_only'] and taint == 0
    assert all(re.fullmatch(r'\[\s*\d+\.\d+\] qcom,slim-ngd-ctrl 171c0000.slim-ngd: unable to prepare channel', line) for line in failed)
if taint:
    assert state['warning_count'] == 1 and state['known_warning_transition_only']
    assert after.count('WARNING:') == delta.count('ida_free called for id=1 which is not allocated.') == 1
    assert re.search(r'WARNING: lib/idr.c:594 at ida_free\+', delta)
    assert all(name + '+' in delta for name in ['ida_free', 'slim_unregister_controller', 'slim_pd_status', 'pdr_notifier_work'])
else:
    assert state['warning_count'] == 0 and after.count('WARNING:') == 0
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1), ('partition-check.txt', 3), ('new-module-check.txt', 784)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
    if failed:
        assert data['completion-' + name].count(b': OK') == count and b'FAILED' not in data['completion-' + name]
report = dict(stage=145, quiesce_audit_pass=True, current_kernel=140, target_kernel=145,
              same_current_boot=True, gui_user_and_drm_crtcs_quiesced=True,
              no_drm_userspace_clients=True, drm_minor=1, pcm_closed_before_adsp_stop=True,
              audio_card_absent_after_adsp_stop=True, amps_idle_after_stop=True,
              all_remoteprocs_offline=True, sensor_power_zero=True,
              nv6_source4_vendor1_preserved=True, boot_logdump_persist_hashes_still_before=True,
              same132_module_checks_pass=True, taint=taint, shutdown_state_validated=True,
              known_warning_transition_only=state['known_warning_transition_only'],
              old_slimbus_warning_not_fixed=True, clean_runtime_accepted=False,
              archive_sha256=hashlib.sha256((out / 'quiesce-private.tar').read_bytes()).hexdigest(),
              goal_complete=False)
report.update(sealed_shutdown_faults_transition_only=bool(failed),
              shutdown_tx_prepare_failures=len(failed), old_shutdown_fault_not_fixed=bool(failed),
              each_shutdown_failure_channel_state_not_recorded=bool(failed))
(ref / 'quiesce-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'quiesce-validation.json').write_text(json.dumps(dict(report, boot_id=data['boot-id-private.txt'].decode().strip()), indent=2) + '\n')
print('K145_FRESH140_FULL_QUIESCE_GUARD_PASS_TAINT_' + str(taint))
