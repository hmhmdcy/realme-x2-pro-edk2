$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel108'
$prefix="$out\display-same-kernel"
if (Test-Path -LiteralPath "$prefix-reboot.out") {throw 'Fresh reboot prefix required'}
$config=Get-Content -LiteralPath "$out\preparation.json" -Raw | ConvertFrom-Json
$guard=Get-Content -LiteralPath "$out\display-reboot-guard-private.txt"
$expected=(Get-Content -LiteralPath "$out\display-expected-boot-private.txt" -Raw).Trim()
if ($guard.Count -ne 4 -or $guard[2] -ne $expected -or $guard[3] -ne '0' -or
    $guard[0] -notlike "$($config.expected_full_boot_sha256) *" -or
    $guard[1] -notlike "$($config.expected_logdump_sha256) *") {throw 'Fresh device guard mismatch'}
foreach ($spec in @(@('boot-partition-before.img',$config.expected_full_boot_sha256),@('logdump-before.img',$config.expected_logdump_sha256))) {
    if ((Get-FileHash -LiteralPath "$out\$($spec[0])").Hash.ToLowerInvariant() -ne $spec[1]) {throw 'Full backup mismatch'}
}
$identity=Get-Content -LiteralPath "$out\fastboot-identity.json" -Raw | ConvertFrom-Json
$fastboot='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
if ($identity.serial -notmatch '^[a-z0-9]{8}$') {throw 'Private serial missing'}
$events=Get-Content -LiteralPath "$out\display-recovery-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'Fresh F1 receipt missing'}
$stop=Get-Content -LiteralPath "$out\display-stop-connectivity-private.log" -Raw
if ($stop -notmatch 'CONNECTIVITY_STOPPED' -or $stop -notmatch [regex]::Escape($expected)) {throw 'Controlled stop receipt missing'}
function Invoke-DisplayFastboot([string]$name,[string[]]$arguments) {
    $process=$null
    try {
        if (Test-Path -LiteralPath "$prefix-$name.out") {throw 'Fresh process prefix required'}
        $process=Start-Process -FilePath $fastboot -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$prefix-$name.out" -RedirectStandardError "$prefix-$name.err"
        if (!$process.WaitForExit(15000)) {throw 'Fastboot command timed out'}
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {throw 'Fastboot command failed'}
        return ((Get-Content -LiteralPath "$prefix-$name.out" -Raw)+(Get-Content -LiteralPath "$prefix-$name.err" -Raw))
    } finally {
        if ($process) {
            if (!$process.HasExited) {$process.Kill();$process.WaitForExit()}
            $process.Dispose()
        }
    }
}
# Bounded discovery; never repeat the F1 request or write any partition.
$found=$false
for ($attempt=0;$attempt -lt 20;$attempt++) {
    $devices=Invoke-DisplayFastboot "devices-$attempt" @('devices')
    if ($devices -match ('^'+[regex]::Escape($identity.serial)+'\s+fastboot\s*$')) {$found=$true;break}
    Start-Sleep -Seconds 1
}
if (!$found) {throw 'Expected fastboot device did not enumerate'}
$product=Invoke-DisplayFastboot 'product' @('-s',$identity.serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile\s') {throw 'Fastboot product mismatch'}
$null=Invoke-DisplayFastboot 'reboot' @('-s',$identity.serial,'reboot')
Write-Output 'SAME_KERNEL_REBOOT_SENT_NO_PARTITIONS_WRITTEN'
