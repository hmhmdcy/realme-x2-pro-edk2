from pathlib import Path
import hashlib
import json
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
def read(name):
    path = out / name
    data = {}
    with tarfile.open(path) as archive:
        for entry in archive:
            assert not entry.issym() and not entry.islnk()
            if not entry.isfile():
                continue
            key = entry.name.removeprefix('./')
            assert not Path(key).is_absolute() and '..' not in Path(key).parts
            assert key not in data
            data[key] = archive.extractfile(entry).read()
    verified = set()
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, key = line.split('  ', 1)
        key = key.removeprefix('./')
        assert key not in verified
        assert hashlib.sha256(data[key]).hexdigest() == digest
        verified.add(key)
    assert verified == set(data) - {'SHA256SUMS'}
    return data, hashlib.sha256(path.read_bytes()).hexdigest(), len(verified)

data, digest, count = read('wrap-up15.tar.gz')
final, final_digest, final_count = read('wrap-up15-trace-final.tar.gz')
assert data['boot-id-private.txt'] == final['boot-id-private.txt']
with tarfile.open(out / 'display-linear15-failed.tar') as archive:
    assert data['boot-id-private.txt'] == archive.extractfile('./boot-id-private.txt').read()
assert b'#113 ' in data['uname.txt']
assert b'/dev/sda16 / f2fs rw,' in data['mounts-private.txt']
assert data['slpi.txt'].strip() == b'offline'
assert data['sensor-power.txt'].strip() == b'vdd=0 vddio=0'
assert data['slpi-firmware.txt'].strip() == b'qcom/sm8150/realme/samurai/slpi.mdt'
assert data['launcher-restored.txt'].strip() == b'ORIGINAL_LAUNCHER_MATCH'
assert data['fbcon.txt'].strip() == b'0'
assert data['phoc.txt'].strip() and data['phosh.txt'].strip()
assert b'status: started' in data['greetd-status.txt']
assert data['pcm.txt'].splitlines() == [b'closed', b'closed']
amps = data['amps.txt'].splitlines()
assert len(amps) == 2 and all(b'powered=0 muted=1' in line for line in amps)
assert data['nv-check.txt'].count(b': OK') == 6
assert data['source-check.txt'].count(b': OK') == 4
idle = json.loads(data['idle-restoration.json'])
assert idle['after'] == 'uint32 60' and idle['original_idle_policy_restored']
assert idle['lock_unchanged']
instances = ['display', 'radio', 'display-clock15', 'display-clock15b', 'display-linear15']
for name in instances:
    assert data[name + '-tracing-after.txt'].strip() == b'0'
    assert final[name + '-tracing-after.txt'].strip() == b'0'
    assert not final[name + '-events-after.txt'].strip()
    assert not any(line.startswith(b'snapshot:') for line in final[name + '-trigger-after.txt'].splitlines())
assert data['display-events-after.txt'].strip() == b'dpu:dpu_enc_frame_done_timeout'
assert b'snapshot:count=0' in final['display-trigger-before.txt']
snapshot_digest = hashlib.sha256(data['display-snapshot-private.txt']).hexdigest().encode()
assert final['display-snapshot-before.sha256'].strip() == snapshot_digest
assert final['display-snapshot-after.sha256'].strip() == snapshot_digest
assert final['snapshot-preserved.txt'].strip() == b'SNAPSHOT_BYTES_PRESERVED'
for name in ('display', 'radio'):
    assert name + '-trace-private.txt' in data and name + '-snapshot-private.txt' in data

processes = data['processes-private.txt'].decode().splitlines()
assert not any('hexagonrpcd' in line or 'drm-clock-probe15' in line or 'ssc-attribute-census.py' in line for line in processes)
before = data['dmesg-before-private.txt']
after = final['dmesg-after-private.txt']
assert data['state-before.txt'].splitlines()[-1] == b'512'
assert data['state-after.txt'].splitlines()[-1] == b'512'
assert final['state-after.txt'].splitlines()[-1] == b'512'
assert final['phosh.txt'].strip()
assert final['slpi.txt'].strip() == b'offline'
assert final['sensor-power.txt'].strip() == b'vdd=0 vddio=0'
assert after.count(b'frame done timeout') == 9
assert after.count(b'*** gpu fault') == 1
assert 'dump-sources.txt' not in data and not any(name.startswith('devcd') for name in data)
assert 'devcoredump-sources.txt' not in final
report = dict(
    archive_sha256=digest,
    archive_files=len(data), nested_files_verified=count,
    trace_final_archive_sha256=final_digest, trace_final_nested_files_verified=final_count,
    boot_checkpoint='reboot-audio-clean-15',
    phosh_process_present=True, greetd_started=True, f2fs_root_rw=True,
    slpi_offline_sensor_power_off=True, original_firmware_selector_restored=True,
    original_launcher_restored_byte_for_byte=True, idle_delay_restored_seconds=60,
    lock_policy_unchanged=True, runtime_fbcon_bind=0,
    nv6_sources4_unchanged=True, both_pcm_closed=True, both_amplifiers_off_muted=True,
    diagnostic_trace_instances_stopped=instances, all_trace_events_disabled=True,
    original_spent_snapshot_trigger_removed=True,
    first_wrap_up_event_remaining='display:dpu_enc_frame_done_timeout (spent snapshot trigger)',
    original_snapshot_bytes_unchanged_after_trigger_removal=True,
    display_radio_trace_and_snapshot_preserved=True, sensor_drm_trial_processes_absent=True,
    taint_after=512, total_dpu_timeouts=9, gpu_faults=1,
    new_dpu_timeouts_during_wrap_up=after.count(b'frame done timeout') - before.count(b'frame done timeout'),
    new_gpu_faults_during_wrap_up=after.count(b'*** gpu fault') - before.count(b'*** gpu fault'),
    new_kernel_warnings_during_wrap_up=after.count(b'WARNING:') - before.count(b'WARNING:'),
    gpu_devcoredump_captured=False,
    gpu_devcoredump_earlier_inventory_bytes=323539,
    gpu_devcoredump_status='Earlier read-only inventory observed GPU devcoredump; absent when wrap-up collection began. Binary not captured.',
    physical_display_after_later_trials_verified=False,
    permanent_display_fix_accepted=False, complete_rootfs_image_delivered=False,
    wrap_up_complete=True, goal_complete=False,
)
(ref / 'wrap-up15-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
