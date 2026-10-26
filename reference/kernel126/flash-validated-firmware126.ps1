param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='embedded-tpg')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel126'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if($serial -notmatch '^[a-z0-9]{8}$'){throw 'Device identity guard absent'}
$package=Get-Content -LiteralPath "$out\firmware-deployment-package-validation.json" -Raw | ConvertFrom-Json
$quiesce=Get-Content -LiteralPath "$out\firmware-quiesce-validation.json" -Raw | ConvertFrom-Json
$bootId=(Get-Content -LiteralPath "$out\current-boot-id-private.txt" -Raw).Trim()
if(!$package.fresh_current126_preflash_pass -or !$package.only_embedded_dtb_changed -or !$package.other_uefi_executable_bytes_unchanged -or !$package.canonical_source_and_original_build_restored -or !$package.all770_matching_modules -or $package.boot_id -ne $bootId -or ($package.flash_partitions -join ',') -ne 'boot'){throw 'Fresh current126 firmware package audit incomplete'}
if(!$quiesce.quiesce_audit_pass -or !$quiesce.gui_user_and_drm_crtcs_quiesced -or !$quiesce.no_drm_userspace_clients -or !$quiesce.all_remoteprocs_offline -or $quiesce.boot_id -ne $bootId){throw 'Current126 quiesce absent'}
foreach($item in @(@("$out\boot-partition-before-private.img",$package.before_boot_sha256),@("$out\logdump-k126-internal-tpg.img",$package.logdump_sha256),@("$out\boot-partition-k126-embedded-tpg.img",$package.boot_sha256))){if((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]){throw 'Firmware or rollback bytes changed'}}
if((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -notmatch 'K126_F2FS_FROZEN_FOR_BOOTLOADER'){throw 'Fresh freeze receipt absent'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if(!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count){throw 'Fresh single F1 receipt absent'}
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
$image="$out\boot-partition-k126-embedded-tpg.img"
if((Get-Item -LiteralPath $image).Length -ne 100663296){throw 'Image length changed'}
$text=Invoke-CheckedFastboot 'flash-boot' @('-s',$serial,'flash','boot',$image) 90
if($text -notmatch "Writing 'boot'\s+OKAY" -or $text -match 'FAILED'){throw 'Flash completion unconfirmed'}
Write-Output 'K126_EMBEDDED_DTB_BOOT_FLASH_CONFIRMED'
$null=Invoke-CheckedFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=126;release='7.3.0-rc6-rmx1931-samurai-k126+';partitions=@('boot');only_embedded_dtb_changed=$true;logdump_changed=$false;userdata_bulk_flash_or_erase=$false;stable115_118_rollback_preserved=$true;boot_sha256=$package.boot_sha256;logdump_sha256=$package.logdump_sha256;root_frozen_before_reboot=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'K126_EMBEDDED_DTB_BOOT_FLASH_AND_REBOOT_COMPLETE_RUNTIME_VALIDATION_PENDING'
