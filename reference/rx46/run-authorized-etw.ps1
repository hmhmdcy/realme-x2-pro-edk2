param()
$ErrorActionPreference='Stop'
$rx46OperatorLog='E:\edk2-samurai-out\rx46\authorized-etw-operator.log'
try {
    & 'E:\RealmeX2Pro edk2\linux-port\scripts\eud-etw-step.ps1' -Out 'E:\edk2-samurai-out\rx46\etw-r46g-capture' *> $rx46OperatorLog
    'Capture helper returned normally.' | Add-Content -LiteralPath $rx46OperatorLog
    exit 0
} catch {
    $_ | Format-List * -Force | Out-String | Add-Content -LiteralPath $rx46OperatorLog
    exit 1
}
