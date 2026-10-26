$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel152'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath 'E:/RealmeX2Pro edk2/reference/kernel147/build-package-validation.json' | ConvertFrom-Json
$image='E:/edk2-samurai-out/kernel147/logdump-k147-iova-align.img'
if ((Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $build.logdump_sha256) {throw 'Stable image verification failed'}
function CheckedFastboot([string]$Name,[string[]]$Arguments,[int]$Timeout=8000) {
    $log="$out/rollback147-complete-$Name-private.log"
    $err="$out/rollback147-complete-$Name-private.err"
    if ((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $err)) {throw 'Existing operation log; inspect state'}
    $p=Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $err
    try {
        if (!$p.WaitForExit($Timeout)) {throw "Fastboot $Name timed out; inspect state"}
        $p.WaitForExit()
        if ($p.ExitCode -ne 0) {throw "Fastboot $Name failed"}
        (Get-Content -Raw -LiteralPath $log)+(Get-Content -Raw -LiteralPath $err)
    } finally {if(!$p.HasExited){$p.Kill();$p.WaitForExit()};$p.Dispose()}
}
$devices=CheckedFastboot devices @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Identity mismatch'}
$product=CheckedFastboot product @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
$geometry=CheckedFastboot size @('-s',$serial,'getvar','partition-size:logdump')
if ($geometry -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 67108864) {throw 'Geometry mismatch'}
$flash=CheckedFastboot flash @('-s',$serial,'flash','logdump',$image) 30000
if ($flash -notmatch "Writing 'logdump'\s+OKAY" -or $flash -match 'FAILED') {throw 'Rollback write not confirmed'}
$null=CheckedFastboot reboot @('-s',$serial,'reboot')
Write-Output K152_ROLLBACK147_WRITE_AND_REBOOT_CONFIRMED
