from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128'
s=(r/'reference/kernel126/flash-validated126.ps1').read_text()
s=s.replace("$Prefix='tpg-first'","$Prefix='key-delete-first'").replace('kernel126','kernel128').replace('k126','k128').replace('K126','K128')
s=s.replace('$build.candidate -ne 126','$build.candidate -ne 128').replace('$before.current_kernel -ne 118','$before.current_kernel -ne 126').replace('$before.target_kernel -ne 126','$before.target_kernel -ne 128')
s=s.replace('$build.other_769_module_executable_sections_byte_equal','$build.all_770_module_executable_sections_byte_equal126').replace('$build.fixed_ipa_executable_sections_preserved','$build.fixed_ipa_camss_cphy_cpas_preserved')
s=s.replace('$boot.uefi_boot115_reused_byte_exact','$boot.boot126_embedded_dtb_reused_byte_exact').replace(' -or !$boot.camss_enabled_for_internal_tpg -or !$boot.cci_and_external_sensors_disabled',' -or !$boot.dtb_byte_identical126')
a=s.index('if(!$stage.');b=s.index('\n',a)
s=s[:a]+"if(!$stage.live_staging_audit_pass -or !$stage.new128_directory_all_files_match_validated_archive -or !$stage.old118_and126_directories_preserved -or !$stage.bluetooth_release_path_unchanged){throw 'Parallel module staging proof absent'}"+s[b:]
s=s.replace('logdump-k128-internal-tpg.img','logdump-k128-key-delete.img').replace('kernel_build=126','kernel_build=128').replace('old118_modules_preserved=$true','old118_and126_modules_preserved=$true').replace('Fresh118','Fresh126').replace('Current118','Current126')
assert 'kernel_build=128' in s and '$build.candidate -ne 128' in s and '$before.current_kernel -ne 126' in s
assert "@('-s',$serial,'flash','logdump',$image)" in s and "'flash','boot'" not in s
(ref/'flash-validated128.ps1').write_text(s)
print('K128_LOGDUMP_ONLY_IDENTITY_GEOMETRY_FREEZE_ROLLBACK_STAGING_FLASHER_READY',flush=True)
