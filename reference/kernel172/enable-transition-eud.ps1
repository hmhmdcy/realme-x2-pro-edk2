$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel172'
$prefix='headset-first'
$base="$out/$prefix-com-up"
if (Test-Path -LiteralPath "$base.out") {throw 'One EUD enable attempt per fresh transition'}
$process=$null
try {
    $process=Start-Process -FilePath 'E:/eud-host/eudtool.exe' -ArgumentList @('com-up') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
    if (!$process.WaitForExit(5000)) {throw 'EUD enable timed out; inspect state before any further action'}
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {throw 'EUD enable failed; preserve observation'}
    $enum=(& 'C:/Program Files/usbipd-win/usbipd.exe' list | Out-String).Replace("`r",'')
    $enum | Set-Content -LiteralPath "$base-enumeration-private.txt" -Encoding utf8NoBOM
    $items=[regex]::Matches($enum,'(?m)^6-5\s+05c6:9505\s+[^\n]*$')
    if ($items.Count -ne 1 -or $items[0].Value.TrimEnd() -notlike '*Shared') {throw 'Unique shared transition EUD endpoint absent'}
    Write-Output 'K172_TRANSITION_EUD_ENABLED_ONCE_SHARED_ENDPOINT_VERIFIED'
} finally {
    if ($process) {if (!$process.HasExited) {$process.Kill();$process.WaitForExit()};$process.Dispose()}
}
