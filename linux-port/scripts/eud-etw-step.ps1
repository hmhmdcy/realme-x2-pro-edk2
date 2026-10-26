#Requires -RunAsAdministrator
<#
One Windows-native EUD OUT plus an RX counter query, under bounded USB ETW.
Uses built-in providers; does not install/change filters, reset USB or flash.
Keep the ETL local: these providers can also record other USB devices.
Microsoft instructions: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-capture-a-usb-event-trace
#>
param(
    [string]$Port = 'COM14',
    [string]$Out = ('E:\edk2-samurai-out\rx46\etw-r46g-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Windows requires an administrator terminal to start USB ETW.'
}
$Out = [IO.Path]::GetFullPath($Out)
$folder = [IO.Path]::GetDirectoryName($Out)
$stem = [IO.Path]::GetFileName($Out)
if (!(Test-Path -LiteralPath $folder -PathType Container)) { throw 'Output directory does not exist.' }
if (@(Get-ChildItem -LiteralPath $folder | Where-Object { $_.Name.StartsWith($stem + '.') }).Count) {
    throw 'Output prefix already exists; choose a fresh -Out.'
}
$device = @(Get-PnpDevice -PresentOnly -Class Ports | Where-Object {
    $_.InstanceId -match 'VID_05C6&PID_9505' -and $_.Status -eq 'OK' -and
    $_.FriendlyName -match ('\(' + [regex]::Escape($Port) + '\)')
})
if ($device.Count -ne 1) { throw 'No unique healthy EUD 9505 port; verify usbipd is detached.' }
$probe = Join-Path $PSScriptRoot 'eud-step.ps1'
if (!(Test-Path -LiteralPath $probe)) { throw 'Missing eud-step.ps1.' }
$session = 'EUD-RX46-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $PID
$logman = Join-Path $env:SystemRoot 'System32\logman.exe'
$traceLog = $Out + '.trace-log.txt'
$started = $false
$complete = $false
$traceStopped = $true
$nativeHex = '90 0a 65 63 68 6f 20 52 34 36 47 0a'
$utc = [DateTime]::UtcNow.ToString('o')

function Invoke-TraceUpdate([string[]]$TraceArguments) {
    $result = & $logman @TraceArguments 2>&1
    $code = $LASTEXITCODE
    $result | Tee-Object -FilePath $traceLog -Append
    if ($code -ne 0) { throw "logman update failed: $code" }
}

try {
    # Set the cleanup flag immediately after native start, before file output.
    $result = & $logman start $session -p Microsoft-Windows-USB-USBXHCI 0x81 `
        -o ($Out + '.etl') -f bincirc -max 64 -nb 16 64 -bs 64 -ets 2>&1
    $code = $LASTEXITCODE
    $started = $code -eq 0
    $traceStopped = !$started
    $result | Tee-Object -FilePath $traceLog -Append
    if (!$started) { throw "Windows USB ETW start failed: $code" }
    Invoke-TraceUpdate -TraceArguments @('update',$session,'-p','Microsoft-Windows-USB-UCX','0x81','-ets')
    Invoke-TraceUpdate -TraceArguments @('update',$session,'-p','Microsoft-Windows-USB-USBHUB3','0x1','-ets')
    # Exactly one original native frame. Do not retry the command in this trace.
    & $probe -Port $Port -Hex $nativeHex -Repeat 1 -Seconds 12 `
        -Ack 'data=65 63 68 6f 20 52 34 36 47 0a' -Out ($Out + '.native.raw') |
        Tee-Object -FilePath ($Out + '.native-run.txt')
    # This only measures RX counters and clears any incomplete shell input.
    & $probe -Port $Port -Hex '90 01 15' -Repeat 5 -Seconds 24 -RetryJitterMs 800 `
        -Ack 'tty byte=15' -Out ($Out + '.metrics.raw') |
        Tee-Object -FilePath ($Out + '.metrics-run.txt')
    $complete = $true
} finally {
    if ($started) {
        $stopResult = & $logman stop $session -ets 2>&1
        $stopCode = $LASTEXITCODE
        $traceStopped = $stopCode -eq 0
        $stopResult | Tee-Object -FilePath $traceLog -Append
        if ($stopCode -ne 0) { Write-Warning "ETW stop failed: $stopCode; session=$session" }
    }
    $etl = @(Get-ChildItem -LiteralPath $folder | Where-Object {
        $_.Name.StartsWith($stem) -and $_.Extension -eq '.etl'
    } | Select-Object FullName,Length)
    [ordered]@{
        utc=$utc; session=$session; port=$Port; out=$Out; completed=$complete; trace_stopped=$traceStopped;
        providers=@('USBXHCI:Default,PartialDataBusTrace','UCX:Default,PartialDataBusTrace','USBHUB3:Default');
        native_hex=$nativeHex; native_repeat=1; counter_repeat_limit=5;
        etl=$etl; note='Local host-controller/client USB events, not a physical wire analyser. Keep all-device ETL local.'
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath ($Out + '.manifest.json') -Encoding UTF8
    Write-Output "ETW capture prefix: $Out"
}
