[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$Image = "E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261119-clean\samurai-stable-f2fs-partuuid.simg",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\!tmp\fastboot.exe",
    [string]$ExpectedHash = "54d9768acedaccd4245960ff13558c03c5b750214b151c5c05847bfce71e0fc3",
    [int64]$ExpectedBytes = 3644199308,
    [switch]$Confirm,
    [int]$ChunkMb = 64,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"

function Get-FastbootDevices {
    param([string]$Tool)
    $out = Invoke-Fastboot -Tool $Tool -Arguments @("devices")
    $rows = foreach ($line in ($out -split "`r?`n")) {
        $fields = $line.Trim() -split "\s+"
        if ($fields.Count -ge 2 -and $fields[1] -eq "fastboot") {
            [pscustomobject]@{ Serial = $fields[0]; State = $fields[1] }
        }
    }
    return @($rows)
}

# fastboot writes normal output to stderr, which PowerShell turns into a
# NativeCommandError under $ErrorActionPreference = "Stop".  Capture both
# streams explicitly and only fail on a non-zero exit code.
function Invoke-Fastboot {
    param([string]$Tool, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $Tool @Arguments 2>&1 | ForEach-Object { "$_" } | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "fastboot $($Arguments -join ' ') failed with exit code $code`n$out" }
    return $out
}

if (-not (Test-Path -LiteralPath $Image)) { throw "image not found: $Image" }
if (-not (Test-Path -LiteralPath $Fastboot)) { throw "fastboot not found: $Fastboot" }

$item = Get-Item -LiteralPath $Image
if ($item.Length -ne $ExpectedBytes) {
    throw "image size mismatch: expected $ExpectedBytes, got $($item.Length)"
}
$hash = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $ExpectedHash) { throw "image hash mismatch: got $hash" }
Write-Host "image verified: $([math]::Round($item.Length/1GB,2)) GiB sha256=$hash"

$devices = Get-FastbootDevices -Tool $Fastboot
if ($devices.Count -eq 0) {
    throw "no fastboot device. Power the phone off, then hold Volume-Down + Power until fastboot appears."
}
$target = $devices | Where-Object { $_.Serial -eq $Serial }
if (-not $target) {
    throw "expected serial $Serial not in fastboot. Found: $($devices.Serial -join ', ')"
}

Write-Host "target: $Serial"
Write-Host "about to flash ONLY userdata; boot, logdump and DTB are untouched."
$props = @{}
foreach ($key in @("product", "current-slot", "slot-count", "max-download-size")) {
    # Optional variables may not exist on this bootloader; record, never abort.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $value = & $Fastboot -s $Serial getvar $key 2>&1 | ForEach-Object { "$_" } | Out-String
    } finally {
        $ErrorActionPreference = $previous
    }
    $props[$key] = $value.Trim()
}
$props.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key): $($_.Value)" }

# The logical image is ~111 GiB while fastboot has a small per-request
# download limit, so the sparse image must be sent in chunks.
#
# Do NOT size chunks from max-download-size.  Modern fastboot hard-codes the
# write timeout at 5000 ms (previously 500 + len*8), and it does not retry.
# Each chunk is first buffered in bootloader RAM and then written to
# userdata; a 767 MB chunk needs far longer than 5 s to land on this
# partition, so the write times out with AdbWriteEndpointSync failed (121)
# and leaves userdata partially written.  Small chunks keep every individual
# write inside the timeout, at the cost of more round trips.
$maxDownload = 0
if ($props["max-download-size"] -match '([0-9]+)') { $maxDownload = [int64]$Matches[1] }
$chunkArgs = @()
if ($item.Length -gt 64MB) {
    $chunkMb = $ChunkMb
    if ($chunkMb -lt 16) { $chunkMb = 16 }
    if ($maxDownload -gt 0 -and $chunkMb -gt ($maxDownload / 1048576)) {
        $chunkMb = [int]([math]::Floor($maxDownload / 1048576))
    }
    $chunkArgs = @("-S", "${chunkMb}M")
    Write-Host "sending sparse image in ${chunkMb}M chunks (fastboot write timeout is 5000 ms)"
}

if (-not $Confirm) {
    Write-Host "dry run only; nothing was written." -ForegroundColor Yellow
    Write-Host 'to flash: .\flash-plasma-rootfs.ps1 -Confirm:$true'
    return
}

Invoke-Fastboot -Tool $Fastboot -Arguments (@("-s", $Serial) + $chunkArgs + @("flash", "userdata", $Image)) | Out-Null

# This bootloader's USB command channel becomes unusable around a 2.6 GB
# write.  Observed failures are usb_read failed (31) and, in a later session
# that had a healthy channel before flashing, AdbWriteEndpointSync failed
# (121) on every command afterwards - including "reboot", "continue" and
# "getvar".  The flash itself always completes; only the command channel
# dies.  The device then has to be powered off with the power key.
#
# Do not treat "reboot" as a reliable exit.  It is opt-in and the default
# path tells the operator to power-cycle.
if ($Reboot) {
    Write-Host "flash complete; requesting reboot (may fail on this bootloader)"
    try {
        Invoke-Fastboot -Tool $Fastboot -Arguments @("-s", $Serial, "reboot") | Out-Null
        Write-Host "reboot accepted" -ForegroundColor Green
    } catch {
        Write-Host "reboot failed; power-cycle the device instead" -ForegroundColor Yellow
    }
} else {
    Write-Host "flash complete; userdata written." -ForegroundColor Green
    Write-Host "This bootloader's USB command channel wedges after the write"
    Write-Host "(reboot/continue/getvar all fail with error 121)."
    Write-Host "Hold Power for ~15 s to force off, then power on normally."
}
