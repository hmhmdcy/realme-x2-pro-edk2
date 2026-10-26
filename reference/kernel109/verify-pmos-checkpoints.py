"""Audit private archives and emit only a sanitized hardware checkpoint."""
from pathlib import Path
import array, hashlib, json, tarfile
out = Path('/mnt/e/edk2-samurai-out/kernel109')
public = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel109')
def sha(data): return hashlib.sha256(data).hexdigest()
def archive(name):
    result = {}
    with tarfile.open(out/name) as tar:
        for member in tar:
            if member.isfile():
                key = member.name.removeprefix('./')
                result[key] = tar.extractfile(member).read()
    return result
def checkpoint(name, prefix):
    content = archive(name)
    sums = content[prefix+'SHA256SUMS'].decode().splitlines()
    for line in sums:
        digest, name = line.split('  ', 1)
        assert sha(content[prefix+name.removeprefix('./')]) == digest
    return {key.removeprefix(prefix): value for key,value in content.items()}, len(sums)
before, count1 = checkpoint('layout-before.tar', 'k109-layout-before/')
after, count2 = checkpoint('layout-after.tar', 'k109-layout-after/')
for disk in ['sda','sdb','sdc','sdd','sde','sdf']:
    for suffix in ['geometry','head','tail']:
        assert before[f'{disk}.{suffix}'] == after[f'{disk}.{suffix}']
assert before['persist.sha256'] == after['persist.sha256']
candidate = json.loads((out/'candidate-validation.json').read_text())
partitions = after['boot-logdump.sha256'].decode()
assert candidate['full_backup_boot_sha256'] in partitions
assert candidate['logdump_sha256'] in partitions
for content in [before, after]:
    assert all(line.endswith(b': OK') for line in content['nv-check.txt'].splitlines())
reboot, count3 = checkpoint('persistent-reboot.tar', 'k109-persistent-reboot/')
assert reboot['system.txt'].decode().splitlines()[1] != before['state.txt'].decode().splitlines()[0]
assert '#109 SMP PREEMPT' in reboot['system.txt'].decode()
assert '/dev/sda16 / f2fs rw' in reboot['system.txt'].decode()
assert reboot['samurai-wifi-boot.log'].rstrip().endswith(b'WIFI_READY')
assert all(line.endswith(b': OK') for line in reboot['nv-check.txt'].splitlines())
log = reboot['dmesg.txt'].decode()
assert 'frame done timeout' not in log and 'gpu fault' not in log and 'hangcheck recover' not in log
assert 'power mode 0x9c' in log
assert 'Synaptics S3706A' in reboot['input.txt'].decode()
phosh = archive('phosh-after-reboot.tar')
assert phosh['tainted.txt'].strip() == b'0'
assert '1080x2400' in phosh['outputs.txt'].decode()
assert 'Scale: 3.000000' in phosh['outputs.txt'].decode()
assert b'/usr/libexec/phosh' in phosh['processes.txt']
assert b'phosh-osk-stevia' in phosh['processes.txt']
audio = archive('desktop-audio-first.tar')
assert audio['play-exit.txt'].strip() == b'0'
assert audio['capture-exit.txt'].strip() in [b'124', b'143']
assert b'state: RUNNING' in audio['play-live.txt']
assert b'state: RUNNING' in audio['capture-live.txt']
assert audio['after.txt'].startswith(b'closed\nclosed\n')
assert audio['after.txt'].count(b'powered=0 muted=1') == 2
assert audio['after.txt'].count(b'failed=0') == 2
assert audio['tainted.txt'].strip() == b'0'
samples = array.array('h', audio['mic-private.s16le'])
assert len(samples) > 48000
stats = dict(frames=len(samples), seconds=len(samples)/48000,
             nonzero=sum(x != 0 for x in samples), distinct=len(set(samples)),
             peak=max(map(abs,samples)), clipped=sum(abs(x)>=32767 for x in samples))
assert stats['nonzero'] > 48000 and stats['distinct'] > 10
latest, count4 = checkpoint('early-diagnostics.tar', 'k109-early-diagnostics/')
desktop = archive('desktop-early-diagnostics.tar')
latest_phosh = archive('phosh-early-diagnostics.tar')
assert latest['persistence-test.txt'].strip() == b'F2FS-K109-PERSISTENCE-TEST'
assert b'#109 SMP PREEMPT' in latest['system.txt']
assert latest['system.txt'].decode().splitlines()[1] != reboot['system.txt'].decode().splitlines()[1]
assert latest_phosh['tainted.txt'].strip() == b'0'
assert latest_phosh['screenshot-status.txt'] == b'' and 'screen.png' in latest_phosh
assert b'/etc/phosh/phoc.ini' in latest_phosh['processes.txt']
assert all(line.endswith(b': OK') for line in latest['nv-check.txt'].splitlines())
assert candidate['full_backup_boot_sha256'] in latest['boot-logdump-persist.sha256'].decode()
assert candidate['logdump_sha256'] in latest['boot-logdump-persist.sha256'].decode()
assert b'HiFi__Speaker__sink' in desktop['sinks.txt'] and b'HiFi__Mic__source' in desktop['sources.txt']
assert desktop['pcm-idle.txt'] == b'closed\nclosed\n'
assert desktop['haptics.txt'].count(b'starts=0') == 1
assert b'Leap status     : Normal' in desktop['clock.txt']
assert b'rc boot logging' in latest['rc.log']
latest_log=latest['dmesg.txt'].decode()
report = dict(stage=109, kernel_build=109, archives_verified=True,
    files_with_nested_hashes_verified=count1+count2+count3+count4,
    userdata_f2fs_flushed_and_booted=True, persistent_rootfs_reboot_pass=True,
    phosh_and_osk_processes_running=True, phosh_1080x2400_scale=3,
    physical_display_and_touch_confirmation_pending=True,
    latest_reboot_display_timeouts=latest_log.count('frame done timeout'),
    latest_reboot_gpu_faults=latest_log.count('*** gpu fault'),
    one_normal_reboot_failed_before_usb_recovered=True,
    recovery_f1_receipt_and_fastboot_reboot_only_pass=True,
    early_ssh_and_rc_logger_latest_normal_reboot_pass=True,
    rescue110_candidate_built_audited_not_deployed=True,
    first_boot_invalid_autostart_gpu_fault_record_preserved=True,
    kernel_taint=0, full_boot_preserved=True, current_logdump_matches_candidate=True,
    gpt_six_lun_heads_tails_identical=True, nv_and_persist_preserved=True,
    desktop_audio_playback_exit=0, desktop_microphone=stats,
    desktop_audio_idle_pcm_closed=True, both_amplifiers_muted_after_idle=True,
    physical_speaker_sound_and_microphone_quality_unconfirmed=True,
    wifi_24g_nm_https_and_reboot_pass=True, wifi_5g_latest_attempt_failed=True,
    wifi_long_term_stability_unproven=True, bluetooth_pair_or_connect=False,
    haptics_new_pulses=False, goal_complete=False,
    archives={name:sha((out/name).read_bytes()) for name in [
        'layout-before.tar','layout-after.tar','persistent-reboot.tar',
        'phosh-after-reboot.tar','desktop-audio-first.tar','early-diagnostics.tar',
        'desktop-early-diagnostics.tar','phosh-early-diagnostics.tar']})
(out/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(public/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ['archives_verified',
    'gpt_six_lun_heads_tails_identical','persistent_rootfs_reboot_pass',
    'phosh_and_osk_processes_running','desktop_microphone','desktop_audio_idle_pcm_closed']},indent=2))
