from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126')
s=(ref/'flash-validated126.ps1').read_text().replace("$Prefix='tpg-first'","$Prefix='embedded-tpg'")
a=s.index('$build=');b=s.index('function Invoke-CheckedFastboot')
s=s[:a]+'''$package=Get-Content -LiteralPath "$out\\firmware-deployment-package-validation.json" -Raw | ConvertFrom-Json
$quiesce=Get-Content -LiteralPath "$out\\firmware-quiesce-validation.json" -Raw | ConvertFrom-Json
$bootId=(Get-Content -LiteralPath "$out\\current-boot-id-private.txt" -Raw).Trim()
if(!$package.fresh_current126_preflash_pass -or !$package.only_embedded_dtb_changed -or !$package.other_uefi_executable_bytes_unchanged -or !$package.canonical_source_and_original_build_restored -or !$package.all770_matching_modules -or $package.boot_id -ne $bootId -or ($package.flash_partitions -join ',') -ne 'boot'){throw 'Fresh current126 firmware package audit incomplete'}
if(!$quiesce.quiesce_audit_pass -or !$quiesce.gui_user_and_drm_crtcs_quiesced -or !$quiesce.no_drm_userspace_clients -or !$quiesce.all_remoteprocs_offline -or $quiesce.boot_id -ne $bootId){throw 'Current126 quiesce absent'}
foreach($item in @(@("$out\\boot-partition-before-private.img",$package.before_boot_sha256),@("$out\\logdump-k126-internal-tpg.img",$package.logdump_sha256),@("$out\\boot-partition-k126-embedded-tpg.img",$package.boot_sha256))){if((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]){throw 'Firmware or rollback bytes changed'}}
if((Get-Content -LiteralPath "$out\\$Prefix-freeze.out" -Raw) -notmatch 'K126_F2FS_FROZEN_FOR_BOOTLOADER'){throw 'Fresh freeze receipt absent'}
$events=Get-Content -LiteralPath "$out\\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if(!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count){throw 'Fresh single F1 receipt absent'}
'''+s[b:]
s=s.replace('$image="$out\\logdump-k126-internal-tpg.img"','$image="$out\\boot-partition-k126-embedded-tpg.img"').replace('(Get-Item -LiteralPath $image).Length -ne 67108864','(Get-Item -LiteralPath $image).Length -ne 100663296').replace("'flash-logdump' @('-s',$serial,'flash','logdump',$image)","'flash-boot' @('-s',$serial,'flash','boot',$image)").replace("Writing 'logdump'","Writing 'boot'").replace('K126_LOGDUMP_FLASH_CONFIRMED','K126_EMBEDDED_DTB_BOOT_FLASH_CONFIRMED').replace('K126_LOGDUMP_FLASH_AND_REBOOT_COMPLETE_RUNTIME_VALIDATION_PENDING','K126_EMBEDDED_DTB_BOOT_FLASH_AND_REBOOT_COMPLETE_RUNTIME_VALIDATION_PENDING')
a=s.index('[ordered]@{flash_success=');b=s.index("Write-Output 'K126_EMBEDDED_DTB_BOOT_FLASH_AND",a)
s=s[:a]+'''[ordered]@{flash_success=$true;kernel_build=126;release='7.3.0-rc6-rmx1931-samurai-k126+';partitions=@('boot');only_embedded_dtb_changed=$true;logdump_changed=$false;userdata_bulk_flash_or_erase=$false;stable115_118_rollback_preserved=$true;boot_sha256=$package.boot_sha256;logdump_sha256=$package.logdump_sha256;root_frozen_before_reboot=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out\\$Prefix-flash-validation.json" -Encoding utf8NoBOM
'''+s[b:]
(ref/'flash-validated-firmware126.ps1').write_text(s)
s=(ref/'poll-new-boot.ps1').read_text().replace('postflash-ssh-','embedded-postflash-ssh-').replace('ssh-recovery-validation.json','embedded-ssh-recovery-validation.json')
(ref/'poll-firmware-new-boot.ps1').write_text(s)
print('K126_BOOT_ONLY_CORRECTION_FLASHER_READY')
