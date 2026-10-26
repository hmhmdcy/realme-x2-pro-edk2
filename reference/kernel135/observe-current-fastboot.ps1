param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='mdss-reset-first-observe')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel135'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' | ConvertFrom-Json).serial
if($serial -notmatch '^[a-z0-9]{8}$'){throw 'Stored device identity invalid'}
function Read-Fastboot([string]$name,[string[]]$argsRead){
 $base="$out\$Prefix-$name";if(Test-Path -LiteralPath "$base.out"){throw 'Fresh observation prefix required'}
 $p=Start-Process -FilePath $fb -ArgumentList $argsRead -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
 try{if(!$p.WaitForExit(15000)){throw 'Read-only fastboot observation timed out'};$p.WaitForExit();if($p.ExitCode -ne 0){throw 'Read-only fastboot observation failed'};return ((Get-Content -Raw -LiteralPath "$base.out")+(Get-Content -Raw -LiteralPath "$base.err"))}
 finally{if(!$p.HasExited){$p.Kill();$p.WaitForExit()};$p.Dispose()}
}
$devices=Read-Fastboot 'devices' @('devices');if($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')){throw 'Current fastboot identity mismatch'}
$product=Read-Fastboot 'product' @('-s',$serial,'getvar','product');if($product -notmatch 'product:\s*msmnile'){throw 'Current fastboot product mismatch'}
foreach($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))){$name=$item[0];$text=Read-Fastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name");if($text -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]){throw 'Current fastboot geometry mismatch'}}
$events=@(Get-Content -LiteralPath "$out\mdss-reset-first-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json})
$submits=@($events | Where-Object {$_.event -eq 'out_submit'});$completions=@($events | Where-Object {$_.event -eq 'out_complete'})
if($submits.Count -ne 1 -or $submits[0].hex -ne '90 02' -or $completions.Count -ne 1 -or $completions[0].length -ne 2){throw 'Single OUT submission/completion evidence absent'}
if((Get-Content -Raw -LiteralPath "$out\mdss-reset-first-freeze.out") -notmatch 'K135_F2FS_FROZEN_FOR_BOOTLOADER'){throw 'Successful freeze receipt absent'}
$receipt=@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -gt 0
$report=[ordered]@{current_fastboot_serial_product_geometry_verified=$true;single_9002_out_completed=$true;frozen_before_single_out=$true;f1_text_receipt_received=$receipt;observed_at_utc=[DateTime]::UtcNow.ToString('o');no_second_out_reset_or_reboot_sent=$true;no_flash_performed_by_observer=$true;goal_complete=$false}
$report | ConvertTo-Json | Set-Content -LiteralPath "$out\independent-fastboot-validation.json" -Encoding utf8NoBOM
$report | ConvertTo-Json | Set-Content -LiteralPath 'E:\RealmeX2Pro edk2\reference\kernel135\independent-fastboot-validation.json' -Encoding utf8NoBOM
Write-Output 'K135_SINGLE_OUT_AFTER_FREEZE_CURRENT_FASTBOOT_IDENTITY_PRODUCT_GEOMETRY_PROVED_F1_TEXT_GAP_RECORDED'
