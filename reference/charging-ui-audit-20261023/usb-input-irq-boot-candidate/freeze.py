"""Bind actual private boot result and provenance, without packaging or device I/O."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = json.loads((HERE / 'result.json').read_bytes())
assert result['passed'] and result['parent_inputs_before'] == result['parent_inputs_after']
assert result['parent_mountinfo_unchanged'] and result['written_boot_fully_reparsed']
assert result['runner_sha256'] == sha(HERE / 'package-boot.py') == 'f93575b4b86c0b22d81cf9f4427aaeb357d81ade0c3fff1d91b36a23d06db266'
assert len(result['commands']) == 10 and all(row['terminal'] and row['returncode'] == 0 for row in result['commands'])
assert result['new_used'] == result['max_used'] == 6684672 and result['new_kernel_size'] == 6680318
assert result['main_verification']['other100_complete_FFS_exact']
assert result['written_main_verification'] == result['main_verification']
assert result['main_verification']['BDS_complete_FFS_and_EFI_exact']
assert result['SEC_complete_FFS_and_offset_exact'] and result['SEC_offset'] == 0xfe8
assert result['shim_compat_ramdisk_exact'] and result['header_only_size_ID_changed'] and result['absolute_tail_exact']
boot = PRIVATE / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img'
with boot.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
assert digest == result['boot_sha256'] and boot.stat().st_size == result['boot_bytes'] == 100663296
pair_leaf = HERE.parent / 'usb-input-irq-board-candidate'
assert sha(pair_leaf / 'pair-manifest.json') == '1d1e65c1e29a25694906f1c3004972e751209b5562e070bec885ced35bcafb16'
assert sha(pair_leaf / 'delivery.json') == '6a6a727dc1de1601fea8aecc7ebda1def85f84a5ada46e03594a6c30b0effc51'
sources = {
    'original501_carrier_delivery': REF / 'charging-session-20261023/gauge-image501-carriers-candidate/delivery.json',
    'original501_boot_result': REF / 'charging-session-20261023/gauge-image501-carriers-candidate/boot-result.json',
    'original_compact_reproduction': PRIVATE / 'eud-boot-compact-baseline-private-01/result.json',
    'original_gzip_reproduction': PRIVATE / 'eud-boot-gzip-baseline-private-01/result.json',
    'R8_manifest': PRIVATE / 'r8-candidate/manifest.json',
    'R8_prepare_source': REF / 'charging-management-20261023/prepare-r8.py',
    'R7_two_file_prepare_source': REF / 'charging-management-20261023/prepare-r7.py',
    'R7_two_file_stage_source': REF / 'charging-session-20261023/source-stage-r7/stage-r7.py',
    'R8_setup_manager_source': REF / 'charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging',
    'R8_OpenRC_source': REF / 'charging-session-20261023/r8-source-integration/rootfs-sources/etc/init.d/samurai-charging',
    'DT_ko_pair': pair_leaf / 'pair-manifest.json',
    'DT_ko_independent_review': REF / 'charging-session-20261023/usb-input-irq-board-independent-review/review-result.json',
}
source_hashes = {name: sha(path) for name, path in sources.items()}
assert source_hashes['original_compact_reproduction'] == 'c81ae504e6bf89253dea83a0f5a6831dd7084ade73ab23d45d22f976c9c1467b'
assert source_hashes['original_gzip_reproduction'] == '3de516c86a7ca1d2fcb6069741aa253c7470f844bd2e809d6969ceb1f9733632'
assert source_hashes['R8_manifest'] == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
assert source_hashes['R8_setup_manager_source'] == '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
(HERE / 'source-result.json').write_text(json.dumps({'passed': True, 'source_sha256': source_hashes,
    'old_baseline_or_function_tests_rerun': False, 'future_rootfs_manifest_created': False}, indent=2) + '\n')
execution = {'passed': True, 'native_exec_session': 9554, 'host_linux_pid': result['host_pid'],
             'returncode': 0, 'same_original_handle_waited': True,
             'tool_process_count': 10, 'all_tools_terminal_zero': True,
             'unique_attempt': True, 'compression_policy_or_geometry_changed': False,
             'boot_large_reads_bounded': True, 'device_SDK_Image_BDS_or_rootfs_package_used': False}
(HERE / 'execution-receipt.json').write_text(json.dumps(execution, indent=2) + '\n')
delivery = {'passed': True, 'frozen': True, 'scope': 'offline native-DTB-only FFS boot plus documented future module/manifest pairing',
            'candidate_boot': {'path': str(boot), 'bytes': boot.stat().st_size, 'sha256': digest},
            'rollback_boot_sha256': '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
            'required_USB_module_sha256': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',
            'DT_ko_pair_manifest_sha256': sha(pair_leaf / 'pair-manifest.json'),
            'native_DTB_sha256': result['native_DTB_sha256'], 'unchanged_BDS_EFI_sha256': result['BDS_EFI_sha256'],
            'new_used': result['new_used'], 'max_used': result['max_used'],
            'files': {str(path.relative_to(HERE)).replace('\\', '/'): sha(path)
                      for path in sorted(HERE.rglob('*')) if path.is_file() and path.name != 'delivery.json'},
            'rootfs_package_manifest_or_activation_transaction_created': False,
            'Image502_prepared_transaction_modified': False, 'device_or_IRQ_latency_accepted': False}
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n')
print(json.dumps({'passed': True, 'delivery_sha256': sha(HERE / 'delivery.json'),
                  'result_sha256': sha(HERE / 'result.json'), 'boot_sha256': digest,
                  'source_sha256': sha(HERE / 'source-result.json')}))
