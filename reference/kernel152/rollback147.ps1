$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel152'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath 'E:/RealmeX2Pro edk2/reference/kernel147/build-package-validation.json' | ConvertFrom-Json
$image='E:/edk2-samurai-out/kernel147/logdump-k147-iova-align.img'
if ((Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $build.logdump_sha256) {throw 'Stable image verification failed'}
$events=Get-Content -LiteralPath "$out/recovery-f1.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1) {throw 'Fresh recovery receipt absent'}
function CurrentFastboot([string]$Name,[string[]]$Arguments) {
    $log="$out/rollback147-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Existing rollback log; inspect state'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Rollback $Name failed"}
    Get-Content -Raw -LiteralPath $log
}
$devices=CurrentFastboot devices @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Identity mismatch'}
$product=CurrentFastboot product @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
$geometry=CurrentFastboot size @('-s',$serial,'getvar','partition-size:logdump')
if ($geometry -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 67108864) {throw 'Geometry mismatch'}
$flash=CurrentFastboot flash @('-s',$serial,'flash','logdump',$image)
if ($flash -notmatch "Writing 'logdump'\s+OKAY" -or $flash -match 'FAILED') {throw 'Rollback write not confirmed'}
$null=CurrentFastboot reboot @('-s',$serial,'reboot')
Write-Output K152_ROLLBACK147_WRITE_CONFIRMED
