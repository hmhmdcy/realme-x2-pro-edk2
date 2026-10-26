from pathlib import Path
import hashlib, json, re

K = Path('/home/cy122/x2pro-linux/linux')
O = Path('/mnt/e/edk2-samurai-out/kernel87')
W = Path('/mnt/e/RealmeX2Pro edk2')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for line in (O / 'handover-hashes.txt').read_text().splitlines():
    digest, remote = line.split('  ', 1)
    local = O / Path(remote).name.removeprefix('k87-')
    assert sha(local) == digest, local
state = (O / 'handover-state.txt').read_text()
assert state.startswith('32bf2d8f-8dde-47dc-9b88-e87db9e95198\n')
assert '#86 SMP PREEMPT' in state and '2140.55 ' in state
assert 'underrun:       0' in state and 'frame_done_cnt:2mode:' in state
assert 'snapshot:count=0\n0\n' in state and '0-005c' not in state
assert 'ls: /lib/modules: No such file or directory' in state
assert (O / 'snapshot-hash.txt').read_text().split()[0] == '550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2'
preserved = json.loads((O / 'preservation-audit.json').read_text())
wifi = json.loads((O / 'wifi-profile-audit.json').read_text())
assert preserved['audit'] == wifi['audit'] == 'PASS'
assert len(wifi['changed_symbols']) == 27 and wifi['firmware_files_verified'] == 35
assert not preserved['candidate']['deployed'] and not wifi['profile_deployed']
assert not wifi['image_built_from_wifi_profile'] and not wifi['firmware_installed']
source_paths = ['arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
                'arch/arm64/boot/dts/qcom/sm8150-mtp.dts',
                'drivers/net/wireless/ath/ath10k/snoc.c',
                'drivers/net/wireless/ath/ath10k/qmi.c',
                'drivers/net/wireless/ath/ath10k/core.c',
                'drivers/net/wireless/ath/ath10k/Kconfig',
                'net/wireless/Kconfig', 'drivers/remoteproc/Kconfig',
                'drivers/remoteproc/qcom_q6v5_pas.c',
                'drivers/soc/qcom/qcom_pd_mapper.c']
source_hashes = {p: sha(K / p) for p in source_paths}
old = json.loads((W / 'reference/kernel81/source-audit.json').read_text())
for p, digest in source_hashes.items():
    if p in old['actual_source_file_sha256']:
        assert digest == old['actual_source_file_sha256'][p], p
for f in old['tqftpserv_sources']['files']:
    private = Path('/mnt/e/edk2-samurai-out/kernel81') / ('tqftpserv-' + Path(f['path']).name)
    assert sha(private) == f['sha256'] and private.stat().st_size == f['bytes']
dt = (K / source_paths[0]).read_text()
for node in ['wifi', 'remoteproc_mpss']:
    assert re.search(r'&' + node + r'\s*\{\s*status = "disabled";', dt)
sources = {'local_kernel_head': preserved['local_kernel_head'],
           'local_source_sha256': source_hashes,
           'tqftpserv_sources': old['tqftpserv_sources'],
           'wireless_primary_documentation': 'https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath10k/boardfiles.html',
           'timer_primary_documentation': 'https://docs.kernel.org/driver-api/basics.html',
           'current_tqftpserv_built_run_installed': False,
           'WRQ_supported_in_original_tqftpserv': True,
           'board_ID_selection_verified_on_handset': False}
(O / 'source-reference-audit.json').write_text(json.dumps(sources, indent=2) + '\n')
for n, expected in [('kernel85', 'b68efb3b534fc882972d1a7bbaced45e7dde78ae949584ba3d524cf917ecfb2a'),
                    ('kernel86', '74ea52c2f439f25a6f7cc8f1438dffb372e8c8d4845a790940c66b9bcf3f392f')]:
    assert sha(W / 'reference' / n / 'SHA256SUMS') == expected
result = {'audit': 'PASS', 'scope': 'capture hashes, offline build/tests/profile and documented limits',
          'handset_kernel_version': 86,
          'handset_boot_ID': '32bf2d8f-8dde-47dc-9b88-e87db9e95198',
          'handset_uptime_seconds': 2140.55, 'display_timeouts': 2, 'display_underruns': 0,
          'trace_on': 0, 'snapshot_trigger_count': 0,
          'snapshot_sha256': (O / 'snapshot-hash.txt').read_text().split()[0],
          'DPU_candidate_build_version': 88, 'DPU_candidate_hardware_verified': False,
          'WiFi_profile_Kconfig_resolved': True, 'WiFi_profile_Image_built': False,
          'WiFi_profile_deployed': False, 'charging_control_verified': False,
          'charging_full_monitor_interface_verified': False,
          'new_partition_write_or_reboot': False, 'new_charging_configuration_write': False,
          'historical_85_86_manifest_unchanged': True,
          'source_reference_audit_sha256': sha(O / 'source-reference-audit.json'),
          'next_hardware_priority': 'Wi-Fi', 'full_hardware_goal_completed': False}
(O / 'wrap-up-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: device #86 captured; snapshots/archives/sources verified; all undeployed limits explicit; Wi-Fi next.')
