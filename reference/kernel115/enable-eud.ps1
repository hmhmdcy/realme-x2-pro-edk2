param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='sensor-power-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel115'
for ($attempt=1; $attempt -le 10; $attempt++) {
    $base="$out\$Prefix-com-up-$attempt"
    if (Test-Path -LiteralPath "$base.out") {throw 'Fresh EUD prefix required'}
    $p=$null
    try {
        $p=Start-Process -FilePath 'E:\eud-host\eudtool.exe' -ArgumentList @('com-up') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
        if (!$p.WaitForExit(5000)) {throw 'EUD control request timed out; inspect before retrying'}
        $p.WaitForExit()
        if ($p.ExitCode -eq 0) {Write-Output 'KERNEL115_EUD_COM_ENABLED'; return}
    } finally {if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}}
    Start-Sleep -Seconds 3
}
throw 'EUD control device not available within bounded wait'
