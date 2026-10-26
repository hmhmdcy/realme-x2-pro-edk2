param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='key-delete-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel128'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if($serial -notmatch '^[a-z0-9]{8}$'){throw 'Device identity guard absent'}
$build=Get-Content -LiteralPath "$out\candidate-package-validation.json" -Raw | ConvertFrom-Json
$boot=Get-Content -LiteralPath "$out\boot-package-validation.json" -Raw | ConvertFrom-Json
$before=Get-Content -LiteralPath "$out\preflash-validation.json" -Raw | ConvertFrom-Json
$stage=Get-Content -LiteralPath "$out\live-staging-validation.json" -Raw | ConvertFrom-Json
$quiesce=Get-Content -LiteralPath "$out\quiesce-validation.json" -Raw | ConvertFrom-Json
$bootId=(Get-Content -LiteralPath "$out\source-boot-id-private.txt" -Raw).Trim()
if(!$build.full_image_modules_dtb_build_pass -or $build.candidate -ne 128 -or $build.release -ne '7.3.0-rc6-rmx1931-samurai-k128+' -or $build.module_count -ne 770 -or !$build.all_770_module_executable_sections_byte_equal126 -or !$build.fixed_ipa_camss_cphy_cpas_preserved){throw 'Candidate build and module contract incomplete'}
if(!$boot.fat_readback_exact -or !$boot.fat_readonly_check_pass -or !$boot.boot126_embedded_dtb_reused_byte_exact -or !$boot.dtb_byte_identical126 -or ($boot.flash_partitions -join ',') -ne 'logdump'){throw 'Candidate boot scope rejected'}
if(!$before.preflash_audit_pass -or $before.current_kernel -ne 126 -or $before.target_kernel -ne 128 -or !$before.live_backups_match -or !$before.gpt18_unchanged -or !$before.nv6_source4_vendor1_preserved -or !$before.persist_unchanged -or $before.boot_id -ne $bootId){throw 'Fresh126 rollback audit absent'}
if(!$stage.live_staging_audit_pass -or !$stage.new128_directory_all_files_match_validated_archive -or !$stage.old118_and126_directories_preserved -or !$stage.bluetooth_release_path_unchanged){throw 'Parallel module staging proof absent'}
if(!$quiesce.quiesce_audit_pass -or !$quiesce.gui_user_and_drm_crtcs_quiesced -or !$quiesce.no_drm_userspace_clients -or !$quiesce.all_remoteprocs_offline -or $quiesce.boot_id -ne $bootId){throw 'Current126 quiesce proof absent'}
foreach($item in @(@("$out\boot-partition-before-private.img",$before.before_boot_sha256),@("$out\logdump-before-private.img",$before.before_logdump_sha256),@("$out\logdump-k128-key-delete.img",$boot.logdump_sha256),@("$out\modules-k128-private.tar.gz",$build.archive_sha256))){if((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]){throw 'Candidate or rollback bytes changed'}}
if((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -notmatch 'K128_F2FS_FROZEN_FOR_BOOTLOADER'){throw 'Freeze receipt absent'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if(!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count){throw 'Fresh single-F1 receipt absent'}
function Invoke-CheckedFastboot([string]$Name,[string[]]$Arguments,[int]$Seconds=15){
 $base="$out\$Prefix-$Name";$process=$null
 if(Test-Path -LiteralPath "$base.out"){throw 'Fresh flash prefix required'}
 try{
  $process=Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
  if(!$process.WaitForExit($Seconds*1000)){throw 'Fastboot timeout: inspect live state before retrying'}
  $process.WaitForExit();if($process.ExitCode -ne 0){throw "Fastboot $Name failed"}
  return ((Get-Content -LiteralPath "$base.out" -Raw)+(Get-Content -LiteralPath "$base.err" -Raw))
 }finally{if($process){if(!$process.HasExited){$process.Kill();$process.WaitForExit()};$process.Dispose()}}
}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached'){throw 'EUD still attached to WSL'}
$devices=Invoke-CheckedFastboot 'devices' @('devices')
if($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')){throw 'Independent enumeration identity mismatch'}
$product=Invoke-CheckedFastboot 'product' @('-s',$serial,'getvar','product')
if($product -notmatch 'product:\s*msmnile'){throw 'Unexpected product'}
foreach($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))){
 $name=$item[0];$text=Invoke-CheckedFastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name")
 if($text -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]){throw 'Partition geometry changed'}
}
$image="$out\logdump-k128-key-delete.img"
if((Get-Item -LiteralPath $image).Length -ne 67108864){throw 'Image length changed'}
$text=Invoke-CheckedFastboot 'flash-logdump' @('-s',$serial,'flash','logdump',$image) 90
if($text -notmatch "Writing 'logdump'\s+OKAY" -or $text -match 'FAILED'){throw 'Flash completion unconfirmed'}
Write-Output 'K128_LOGDUMP_FLASH_CONFIRMED'
$null=Invoke-CheckedFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=128;release=$build.release;partitions=@('logdump');boot_changed=$false;userdata_bulk_flash_or_erase=$false;old118_and126_modules_preserved=$true;boot_sha256=$boot.boot_sha256;logdump_sha256=$boot.logdump_sha256;root_frozen_before_reboot=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'K128_LOGDUMP_FLASH_AND_REBOOT_COMPLETE_RUNTIME_VALIDATION_PENDING'
