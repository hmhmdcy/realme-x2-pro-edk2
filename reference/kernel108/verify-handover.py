#!/usr/bin/env python3
"""Audit private evidence, publish only hardware/protocol metadata."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess
import tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel108'
out = Path('/mnt/e/edk2-samurai-out/kernel108')
kernel = Path('/home/cy122/x2pro-linux/linux')
sha = lambda b: hashlib.sha256(b).hexdigest()

def read(name, manifest=True):
    records = {}
    with tarfile.open(out / (name + '.tar')) as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert not member.issym() and not member.islnk()
            if member.isfile():
                key = str(PurePosixPath(*path.parts[1:]))
                assert key not in records
                records[key] = archive.extractfile(member).read()
    if manifest:
        seen = set()
        for line in records['SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ', 1)
            name = name.removeprefix('./')
            assert name not in seen and sha(records[name]) == digest
            seen.add(name)
        assert seen == records.keys() - {'SHA256SUMS'}
    return records

files = read('checkpoint')
archives = {name: read(name) for name in ('first-radio-trace', 'auto-network', 'final-network')}
for name in archives:
    assert files[name + '.tar'] == (out / (name + '.tar')).read_bytes()
state = files['state.txt'].decode().splitlines()
assert '#106 SMP PREEMPT' in state[0]
assert state[1] == (out / 'runtime-boot-id-after-private.txt').read_text().strip()
assert state[3:] == ['0', 'modem', 'running', 'adsp', 'running']
assert state[1] != (out / 'display-expected-boot-private.txt').read_text().strip()
assert files['boot-finished'] == b'0\n'
assert files['bt-class.txt'] == files['modules.txt'] == b''
assert files['pcm-status.txt'] == b'closed\nclosed\n'
assert b'active=0 starts=0 stops=0 watchdog_stops=0 error=0' in files['haptics-status.txt']
for line in files['amp-status.txt'].decode().splitlines():
    assert 'id=43' in line and 'powered=0 muted=1 starts=0 stops=0 failed=0' in line
assert b'freq=5180\n' in files['wpa-status.txt'] and b'wpa_state=COMPLETED\n' in files['wpa-status.txt']
assert files['bl_power.txt'] == b'0\n' and files['brightness.txt'] == b'400\n'
assert len(files['nv-check.txt'].splitlines()) == 6
assert all(line.endswith(b': OK') for line in files['nv-check.txt'].splitlines())
prep = json.loads((out / 'preparation.json').read_text())
parts = {name: digest for digest, name in (line.split('  ', 1) for line in files['partitions.sha'].decode().splitlines())}
assert parts['/dev/sde11'] == prep['expected_full_boot_sha256']
assert parts['/dev/sde32'] == prep['expected_logdump_sha256']
assert sha((out / 'boot-partition-before.img').read_bytes()) == prep['expected_full_boot_sha256']
assert sha((out / 'logdump-before.img').read_bytes()) == prep['expected_logdump_sha256']
old = read('preflash', manifest=False)
assert parts['/dev/sda2'] == old['persist-before.sha'].decode().split()[0]
with tarfile.open(out.parent / 'kernel107/checkpoint.tar') as archive:
    previous_parts = archive.extractfile('k107-checkpoint/partitions.sha').read().decode()
previous_parts = {name: digest for digest, name in (line.split('  ', 1) for line in previous_parts.splitlines())}
assert parts['/dev/sde17'] == previous_parts['/dev/sde17']
assert archives['first-radio-trace']['nv-source-hashes.txt'] == old['nv-source-hashes.txt']
for digest, name in (line.split('  ', 1) for line in files['services.sha'].decode().splitlines()):
    assert sha((kernel.parent / 'initramfs' / name.lstrip('/')).read_bytes()) == digest
assert subprocess.check_output(['git', 'diff', '--binary'], cwd=kernel) == (out / 'kernel-source-before.patch').read_bytes()
assert (kernel / '.config').read_bytes() == (out / 'config-before').read_bytes()
assert (kernel / 'usr/initramfs_data.cpio').read_bytes() == (out / 'cpio-before').read_bytes()
assert (kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes() == (out / 'dtb-before').read_bytes()
assert sha((kernel / 'arch/arm64/boot/Image').read_bytes()) == prep['image_sha256']
for name, digest in json.loads((out / 'initramfs-before.json').read_text()).items():
    assert sha((kernel.parent / 'initramfs' / name).read_bytes()) == digest
for name, digest in json.loads((out / 'untracked-before.json').read_text()).items():
    assert sha((kernel / name).read_bytes()) == digest

trace = json.loads((out / 'first-radio-trace-trace-analysis.json').read_text())
loss = sum(value for cpu in trace['lost'].values() for value in cpu.values())
assert loss == 0
metadata = trace['selected_protocol_metadata']
announces = [event for event in trace['tx_counts'] if event['node'] == 0 and event['type'] == 4]
assert len(announces) == 1 and announces[0]['count'] == 3 and announces[0]['result'] == 0
assert any('samurai_pdm_response:' in line and 'kernel/elf_loader' in line for line in metadata)
log = files['dmesg.txt'].decode()
assert not re.search(r'4080000\.remoteproc: fatal|17300000\.remoteproc: fatal|Kernel panic|Oops:|Unhandled context fault', log)
ups = [float(value) for value in re.findall(r'\[\s*([0-9.]+)\] remoteproc remoteproc\d+: remote processor modem is now up', log)]
assert len(ups) == 1
assert log.count('remote processor adsp is now up') == 1
failure = archives['auto-network']
final = archives['final-network']
assert failure['result.txt'] == b'ASSOCIATION_NOT_COMPLETED_WITHIN_60_SECONDS\n'
assert final['result.txt'] == b'FINAL_NETWORK_TEST_FAILED\n'
assert b'3 packets transmitted, 0 packets received, 100% packet loss' in final['gateway.txt']
assert b'lease' in final['dhcp.txt'] and b'Address' in final['dns.txt']
assert b'Terminated' in final['http.log'] and not final.get('http.txt', b'')
recovery = read('display-recovery-once', manifest=False)
assert recovery['cycle-exit.txt'] == b'0\n'
assert recovery['snapshot-before.sha256'] == recovery['snapshot-after.sha256']
black = (out / 'display-black-private.txt').read_text()
for message in ('SET_DISPLAY_OFF failed: -110', 'ENTER_SLEEP_MODE failed: -110',
                'Skipping prepare of already prepared panel', 'Skipping enable of already enabled panel'):
    assert message in black
before = read('display-live-detail', manifest=False)
prior_encoder = before['_sys_kernel_debug_dri_1_encoder-0_status'].decode()
prior_dsi = before['dmesg.txt'].decode()
assert 'frame_done_cnt:2' in prior_encoder and 'status=c' in prior_dsi
summary = dict(stage=108, kernel_build=106, checkpoint_archive_audit_pass=True,
               checkpoint_sha256=sha((out / 'checkpoint.tar').read_bytes()),
               checkpoint_files=len(files)-1, embedded_archives=3,
               verified_files_with_embedded_archives=len(files)-1+sum(len(value)-1 for value in archives.values()),
               uptime_seconds=float(state[2].split()[0]), first_mpss_up_seconds=ups[0],
               mpss_running_seconds=float(state[2].split()[0])-ups[0],
               automatic_radio_init_pass=True, manual_mpss_recovery_count=0,
               first_hello_service_announcements_pass=True, trace_loss_count=loss,
               modem_and_adsp_running=True, kernel_taint=0,
               display_dsi_errors_before_reboot=prior_dsi.count('dsi_err_worker: status='),
               display_timeouts_before_reboot=2, display_timeouts_after_reboot=log.count('frame done timeout'),
               display_dsi_errors_after_reboot=log.count('dsi_err_worker'),
               drm_cycle_ioctl_exit=0, display_cycle_optical_pass=False,
               display_cycle_result='user reported black screen; DCS -110 and stale panel flags',
               reboot_optical_result='user confirmed visible black-background Linux console',
               white_pattern_after_reboot_verified=False, permanent_display_fix=False,
               failed_association_window_seconds=60, current_wifi_band_mhz=5180,
               current_wifi_state='COMPLETED', wifi_data_test_pass=False,
               gateway_packets_transmitted=3, gateway_packets_received=0,
               dhcp_lease_obtained=True, dns_answer_obtained=True,
               http_body_bytes=0, http_terminated_after_seconds=20,
               wifi_24g_retested=False, bluetooth_pair_or_connect=False,
               new_haptics_pulses=0, charging_probes_run=False,
               kernel_source_config_dtb_cpio_unchanged=True,
               full_boot_logdump_nv_persist_stock_dtbo_preserved=True,
               partitions_flashed=[], new_kernel_built=False, goal_complete=False)
assert not (ref / 'checkpoint-validation.json').exists()
(ref / 'checkpoint-validation.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n')
manifest = {path.name: dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
            for path in out.glob('*.tar')}
(ref / 'private-archive-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(summary, indent=2, ensure_ascii=False))
