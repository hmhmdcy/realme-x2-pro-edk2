$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel174/recovery'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients -or $q.taint -ne 128) {throw 'Recovery quiesce proof absent'}
$events=Get-Content -LiteralPath "$out/recovery-first-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'One transition receipt required'}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
 $log="$out/$Name-private.log"
 if (Test-Path -LiteralPath $log) {throw 'Fresh operation required'}
 & $fb @Arguments *> $log
 if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
 return Get-Content -Raw -LiteralPath $log
}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Current identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
Write-Output 'K174_RECOVERY_REBOOTED_EXISTING_KERNEL172_WITHOUT_FLASH'
