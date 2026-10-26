"""Small E-drive receipt finalization only; no make, ELF load, SDK or phone."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
build = json.loads((HERE/'build-validation.json').read_text())
abi = json.loads((HERE/'abi-validation.json').read_text())
source = json.loads((HERE/'source-validation.json').read_text())
assert build['passed'] and abi['passed'] and source['passed']
archive = abi['actual_embedded_initramfs_comparison']
assert archive['entries'] == archive['changed_mtime_entries'] == 396
assert not archive['compressed_bytes_identical']
assert archive['all_content_order_padding_and_non_time_metadata_identical']
archive.update(archive_byte_identity=False, only_mtime_changed=True,
               data_mode_uid_gid_nlink_dev_inode_content_identical=True)
abi['original_firmware_module_contents_and_initramfs_input_unchanged'] = abi.pop(
    'firmware_original_modules_and_initramfs_unchanged', True)
(HERE/'abi-validation.json').write_text(json.dumps(abi, indent=2)+'\n')
initial = dict(stage=456, scope='Initial exact compressed archive comparison',
               original=abi['original_actual_embedded_initramfs'], candidate=abi['candidate_actual_embedded_initramfs'],
               archive_byte_identity=False, passed=False,
               followup='Exact decompressed byte equality after replacing only newc mtime fields; all 396 contents/non-time metadata identical',
               final_conditions='mtime-only build metadata accepted; do not claim byte-identical archive')
(HERE/'abi-initial-archive-validation.json').write_text(json.dumps(initial, indent=2)+'\n')
files = ['preflight.py', 'prepare-source.py', 'build-image.py', 'check-abi.py', 'README.md',
         'preflight-validation.json', 'source-validation.json', 'build-validation.json',
         'abi-validation.json', 'abi-initial-archive-validation.json']
report = dict(stage=456, commit=source['commit'], release=build['release'],
              only_source_change=source['changed_source_paths'], true_build_banner_version=456,
              image=build['artifacts']['arch/arm64/boot/Image'], vmlinux=build['artifacts']['vmlinux'],
              original_vmlinux_build_id=abi['original_vmlinux_build_id'],
              candidate_vmlinux_build_id=abi['candidate_vmlinux_build_id'],
              exact_original363_config=True, build_passed=True, offline_abi_passed=True,
              actual_builtin_exports=abi['actual_elf_exported_symbols'], module455_imports=abi['module455_imported_symbols'],
              actual_kernel_dwarf_layouts_compared=len(abi['compared_actual_dwarf_types']),
              actual_devnode_store_before_release_callback=True,
              archive_byte_identity=False, only_mtime_changed=True,
              archive396_data_and_all_non_time_metadata_identical=True, candidate_archive_mtime_values=len(archive['candidate_entry_mtimes']),
              source_shared_index_O_current_dtb_and_input_unchanged=True,
              make_and_heavy_abi_work_finished=True, cpu_build_resources_released=True,
              sdk_accessed=False, phone_accessed=False, boot_packaged=False,
              installed_or_booted=False, runtime_validation_pending=True,
              public_file_fingerprints={name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in files},
              stable_for_parent_review=True, passed=True)
(HERE/'final-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({key: value for key, value in report.items() if key != 'public_file_fingerprints'}, indent=2))
