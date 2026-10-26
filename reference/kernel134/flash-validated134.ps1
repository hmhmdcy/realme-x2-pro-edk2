param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='usb-input-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel134'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if($serial -notmatch '^[a-z0-9]{8}$'){throw 'Device identity guard absent'}
$build=Get-Content -LiteralPath "$PSScriptRoot\kernel-build-validation.json" -Raw | ConvertFrom-Json
$boot=Get-Content -LiteralPath "$out\boot-package-validation.json" -Raw | ConvertFrom-Json
$before=Get-Content -LiteralPath "$out\preflash-validation.json" -Raw | ConvertFrom-Json
$stage=Get-Content -LiteralPath "$out\live-staging-validation.json" -Raw | ConvertFrom-Json
$quiesce=Get-Content -LiteralPath "$out\quiesce-validation.json" -Raw | ConvertFrom-Json
$bootId=(Get-Content -LiteralPath "$out\source-boot-id-private.txt" -Raw).Trim()
if(!$build.full_image_modules_dtb_build_pass -or $build.candidate -ne 134 -or $build.release -ne '7.3.0-rc6-rmx1931-samurai-k134+' -or $build.module_count -ne 770 -or !$build.all_existing_module_executable_sections_equal132 -or !$build.mp2650_driver_unchanged -or !$build.encoded_console_char_5_1_uid_gid_zero_mode0600){throw 'Candidate build and module contract incomplete'}
if(!$boot.fat_readback_exact -or !$boot.fat_readonly_check_pass -or !$boot.only_embedded_dtb_changed -or !$boot.fat_and_embedded_dtb_exactly_match_candidate -or ($boot.flash_partitions -join ',') -ne 'boot,logdump'){throw 'Candidate boot scope rejected'}
if(!$before.preflash_audit_pass -or $before.current_kernel -ne 132 -or $before.target_kernel -ne 134 -or !$before.live_backups_match -or !$before.gpt18_unchanged -or !$before.nv6_source4_vendor1_preserved -or !$before.persist_unchanged -or $before.boot_id -ne $bootId){throw 'Fresh132 rollback audit absent'}
if(!$stage.live_staging_audit_pass -or !$stage.new134_directory_all_files_match_validated_archive -or !$stage.old118_and126_and132_directories_preserved -or !$stage.bluetooth_release_path_unchanged){throw 'Parallel module staging proof absent'}
if(!$quiesce.quiesce_audit_pass -or !$quiesce.gui_user_and_drm_crtcs_quiesced -or !$quiesce.no_drm_userspace_clients -or !$quiesce.all_remoteprocs_offline -or $quiesce.boot_id -ne $bootId){throw 'Current132 quiesce proof absent'}
foreach($item in @(@("$out\boot-partition-before-private.img",$before.before_boot_sha256),@("$out\logdump-before-private.img",$before.before_logdump_sha256),@("$out\logdump-k134-usb-input.img",$boot.logdump_sha256),@("$out\boot-partition-k134-usb-input.img",$boot.boot_sha256),@("$out\modules-k134-private.tar.gz",$build.archive_sha256))){if((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]){throw 'Candidate or rollback bytes changed'}}
if((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -notmatch 'K134_F2FS_FROZEN_FOR_BOOTLOADER'){throw 'Freeze receipt absent'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
$f1ReceiptReceived=@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -gt 0
if(!$f1ReceiptReceived){
 $observed=Get-Content -Raw -LiteralPath "$out\independent-fastboot-validation.json" | ConvertFrom-Json
 $submits=@($events | Where-Object {$_.event -eq 'out_submit'});$completions=@($events | Where-Object {$_.event -eq 'out_complete'})
 if($Prefix -ne 'usb-input-first' -or !$observed.current_fastboot_serial_product_geometry_verified -or !$observed.single_9002_out_completed -or !$observed.frozen_before_single_out -or !$observed.no_second_out_reset_or_reboot_sent -or $submits.Count -ne 1 -or $submits[0].hex -ne '90 02' -or $completions.Count -ne 1 -or $completions[0].length -ne 2){throw 'Missing F1 text requires a proven single completed OUT and independently verified current fastboot'}
 $observedAt=if($observed.observed_at_utc -is [DateTime]){$observed.observed_at_utc.ToUniversalTime()}else{[DateTimeOffset]::Parse($observed.observed_at_utc).UtcDateTime}
 $age=([DateTime]::UtcNow-$observedAt).TotalSeconds
 if($age -lt 0 -or $age -gt 300){throw 'Independent fastboot observation is stale'}
}
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
foreach($item in @(@('boot',"$out\boot-partition-k134-usb-input.img",[int64]100663296),@('logdump',"$out\logdump-k134-usb-input.img",[int64]67108864))){
 $partition=$item[0];$image=$item[1]
 if((Get-Item -LiteralPath $image).Length -ne $item[2]){throw 'Image length changed'}
 $text=Invoke-CheckedFastboot "flash-$partition" @('-s',$serial,'flash',$partition,$image) 90
 if($text -notmatch ("Writing '"+$partition+"'\s+OKAY") -or $text -match 'FAILED'){throw 'Flash completion unconfirmed; inspect actual state before proceeding'}
 Write-Output "K134_FLASH_${partition}_CONFIRMED"
}
$null=Invoke-CheckedFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=134;release=$build.release;partitions=@('boot','logdump');boot_changed=$true;userdata_bulk_flash_or_erase=$false;old118_and126_and132_modules_preserved=$true;boot_sha256=$boot.boot_sha256;logdump_sha256=$boot.logdump_sha256;root_frozen_before_reboot=$true;f1_text_receipt_received=$f1ReceiptReceived;independent_current_fastboot_identity_product_geometry_verified=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'K134_BOOT_LOGDUMP_FLASH_AND_REBOOT_COMPLETE_RUNTIME_VALIDATION_PENDING'
