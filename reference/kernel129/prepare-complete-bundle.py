from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129'
s=(r/'reference/kernel128/record-complete-bundle.py').read_text().replace('kernel128','kernel129').replace('k128','k129').replace('K128','K129').replace('image-export128','image-export129').replace('rootfs_generation=128','rootfs_generation=129').replace('candidate_kernel=128','candidate_kernel=129').replace('encoded128','encoded129').replace('ENCODED128','ENCODED129')
s=s.replace('reference/kernel126/ensure-build-volume.py','reference/kernel129/ensure-rootfs-volume.py').replace('/home/cy122/pmos-samurai-build126','/home/cy122/pmos-samurai-rootfs129').replace('logdump-k129-key-delete.img','logdump-k129-console-node.img')
s=s.replace("assert json.loads((ref/'key-delete-postflash-validation.json').read_text())['current_boot_delete_wait_resolved']", "assert json.loads((ref/'embedded-runtime-validation.json').read_text())['initial_console_warning_count']==0")
s=s.replace("assert json.loads((ref/'nm-auto-restart-validation.json').read_text())['automatic_connect_without_explicit_activation']", "assert json.loads((ref/'reboot-autoconnect-validation.json').read_text())['actual_new_boot_auto_connected_without_explicit_activation']")
s=s.replace("(out/'wifi-dual-band-candidate-private.nmconnection')", "(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection')")
s=s.replace('current128_kernel_and_modules_and_dual_band_profile_deployed=True','current129_kernel_and_modules_deployed_inheriting128_dual_band_profile=True')
s=s.replace('real_pairwise_delete_wait_removed_install_confirmations_preserved=True,real5ghz_https_and_auto_nm_restart_pass=True','initial_console_node_present_and_warning_resolved_on_real129_boot=True,real128_pairwise_delete_fix_driver_source_preserved=True,real129_5ghz_reboot_autoconnect_https_pass=True')
s=s.replace('stable115_118_126_boot_logdump_modules_and127_rootfs_rollback_preserved','stable115_118_126_128_boot_logdump_modules_and127_128_rootfs_rollback_preserved')
s=s.replace('internal_tpg_runtime_accepted_on126_code_preserved_in128','internal_tpg_runtime_accepted_on126_code_preserved_in129')
(ref/'record-complete-bundle.py').write_text(s)
print('K129_COMPLETE_BUNDLE_CHECK_BOUND_TO_REAL_CONSOLE_REBOOT_NETWORK_AND_ENCODED_ROOTFS',flush=True)
