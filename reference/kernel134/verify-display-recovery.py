from pathlib import Path
import hashlib
import json
import tarfile
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
def load(name):
    with tarfile.open(out / name) as tf:
        data = {}
        for m in tf:
            assert (m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
            if m.isfile():
                key = m.name.removeprefix('./')
                assert key not in data
                data[key] = tf.extractfile(m).read()
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, key = line.split('  ', 1)
        assert hashlib.sha256(data[key.removeprefix('./')]).hexdigest() == digest
    return data
early = load('early-display-private.tar.gz')
panel = load('panel-reprobe-private.tar.gz')
session = load('initial-session-private.tar.gz')
assert early['boot-id-private.txt'] == panel['boot-id-private.txt'] == session['boot-id-private.txt']
assert b'boot CTL shutdown failed: -22' in early['dmesg-private.txt']
assert b'Found 0 GPUs' in early['phosh-session-private.txt']
assert b'No such file or directory' in early['drm.txt']
assert panel['bind-exit.txt'] == b'0\n' and panel['final-taint.txt'] == b'0\n'
assert b'Initialized msm 1.13.0 for ae01000.display-controller on minor 0' in panel['dmesg-after-private.txt']
assert b'card0' in panel['drm.txt'] and b'renderD128' in panel['drm.txt']
assert session['phosh.txt'].strip() and session['phoc.txt'].strip() and session['final-taint.txt'] == b'0\n'
assert session['config-final-check.txt'].count(b': OK') == 2 and session['initial-session-marker-private'] == b''
runtime = json.loads((r / 'reference/kernel134/embedded-runtime-validation.json').read_text())
assert runtime['initial_display_boot_failed'] and runtime['single_native_panel_reprobe_required']
assert runtime['phosh_running'] and runtime['phoc_running'] and runtime['drm_resolved'] == 'card0 0'
report = dict(kernel=134, initial_native_display_boot_failed=True, inherited_frame_stalled_then_ctl_reset_poll_failed=True,
              initial_failure_archives_preserved=True, same_boot_recovery=True,
              single_native_panel_bind_exit_zero=True, kernel_completed_msm_registration_on_minor_zero=True,
              current_native_drm_identity_resolved_by_physical_path=True, original_phosh_initial_session_restored=True,
              greetd_config_and_launcher_preserved=True, runtime_only_initial_session_marker_saved=True,
              phosh_phoc_and_taint_zero_verified=True, automatic_full_desktop_startup_accepted=False,
              permanent_display_fix=False, gpu_overall_acceptance=False, goal_complete=False)
(r / 'reference/kernel134/display-recovery-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_INITIAL_DISPLAY_FAILURE_AND_SAME_BOOT_NATIVE_RECOVERY_HONEST_BOUNDARY_PASS', flush=True)
