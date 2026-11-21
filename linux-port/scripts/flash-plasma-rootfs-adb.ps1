[CmdletBinding()]
param(
    [string]$Image = "E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261119-apps2\samurai-stable-f2fs-partuuid.simg",
    [string]$ExpectedHash = "b4f712b4f58a1346d6f2722f55f5de6129faed001bb40c8c7c40d36fadc17ac3",
    [int64]$ExpectedBytes = 3628478076,
    [string]$Adb = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\adb.exe",
    [int]$ChunkMb = 128,
    [switch]$Confirm,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"

function Invoke-Adb {
    param([string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $Adb @Arguments 2>&1 | ForEach-Object { "$_" } | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "adb $($Arguments -join ' ') failed ($code)`n$out" }
    return $out
}

function Invoke-AdbShell {
    param([string]$Command)
    return (Invoke-Adb -Arguments @("shell", $Command)).Trim()
}

# 1. Verify the local image; never write a truncated or stale file.
if (-not (Test-Path -LiteralPath $Image)) { throw "image not found: $Image" }
if (-not (Test-Path -LiteralPath $Adb)) { throw "adb not found: $Adb" }

$item = Get-Item -LiteralPath $Image
if ($item.Length -ne $ExpectedBytes) {
    throw "image size mismatch: expected $ExpectedBytes, got $($item.Length)"
}
$hash = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $ExpectedHash) { throw "image hash mismatch: got $hash" }
Write-Host "image verified: $([math]::Round($item.Length/1GB,2)) GiB sha256=$hash"

# 2. Require a recovery/root shell with simg2img. Do not use fastboot here:
#    this bootloader's fastboot channel wedges after a multi-GB write.
$devices = & $Adb devices 2>&1 | ForEach-Object { "$_" }
$targets = @($devices -split "`r?`n" | Where-Object { $_ -match '\t(recovery|device)$' })
if ($targets.Count -ne 1) {
    throw ("expected exactly one adb device in recovery/device state; got:`n" + ($devices -join "`n") +
           "`nBoot ColorOS recovery with Volume-Down + Power.")
}
$serial = ($targets[0] -split "\t")[0].Trim()
Write-Host "target: $serial"

if ((Invoke-AdbShell "id") -notmatch 'uid=0') { throw "adb shell is not root; flashing needs the recovery root shell" }
if ((Invoke-AdbShell "command -v simg2img") -eq "") { throw "simg2img not found in the device shell" }

$free = Invoke-AdbShell "df -Pk /tmp | tail -1 | awk '{print `$4}'"
if ($free -notmatch '^\d+$') { throw "could not read free space on the device: $free" }
$freeBytes = [int64]$free * 1024
if ($freeBytes -lt $item.Length * 2) {
    throw ("device /tmp needs twice the image size (image + sparse expansion); free=" +
           [math]::Round($freeBytes/1GB,2) + " GiB")
}
Write-Host "device free: $([math]::Round($freeBytes/1GB,2)) GiB"

if (-not $Confirm) {
    Write-Host "dry run only; nothing was written." -ForegroundColor Yellow
    Write-Host "to flash: .\flash-plasma-rootfs-adb.ps1 -Confirm`$true -Reboot"
    return
}

# 3. Stream in chunks; each chunk is size-checked on the device before it is
#    appended. This keeps every adb transaction small and detects truncation.
$chunkBytes = [int64]$ChunkMb * 1MB
$chunkDir = Join-Path $env:TEMP ("samurai-flash-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $chunkDir -Force | Out-Null
Invoke-AdbShell "rm -f /tmp/samurai-flash.simg /tmp/samurai-chunk" | Out-Null

try {
    $source = [System.IO.File]::OpenRead($Image)
    try {
        $buffer = New-Object byte[] $chunkBytes
        $index = 0
        $total = [int64]0
        while ($true) {
            $read = $source.Read($buffer, 0, $buffer.Length)
            if ($read -le 0) { break }
            $local = Join-Path $chunkDir ("chunk-{0:D3}" -f $index)
            $fs = [System.IO.File]::Create($local)
            try { $fs.Write($buffer, 0, $read) } finally { $fs.Dispose() }

            Invoke-Adb -Arguments @("push", $local, "/tmp/samurai-chunk") | Out-Null
            $remoteSize = [int64](Invoke-AdbShell "stat -c %s /tmp/samurai-chunk")
            if ($remoteSize -ne (Get-Item -LiteralPath $local).Length) {
                throw "chunk $index truncated: local=$((Get-Item -LiteralPath $local).Length) remote=$remoteSize"
            }
            Invoke-AdbShell "cat /tmp/samurai-chunk >> /tmp/samurai-flash.simg; rm -f /tmp/samurai-chunk" | Out-Null

            $index++
            $total += $read
            if (($index % 5) -eq 0 -or $read -lt $buffer.Length) {
                Write-Host ("pushed {0:N2} / {1:N2} GiB" -f ($total/1GB), ($item.Length/1GB))
            }
            Remove-Item -LiteralPath $local -Force
        }
    } finally {
        $source.Dispose()
    }

    $pushed = [int64](Invoke-AdbShell "stat -c %s /tmp/samurai-flash.simg")
    if ($pushed -ne $item.Length) { throw "device image size mismatch: expected $($item.Length), got $pushed" }

    Write-Host "verifying SHA256 on the device (this takes a few minutes)..."
    $remoteHash = Invoke-AdbShell "sha256sum /tmp/samurai-flash.simg | cut -d' ' -f1"
    if ($remoteHash -ne $ExpectedHash) { throw "device hash mismatch: got $remoteHash" }
    Write-Host "device hash matches." -ForegroundColor Green

    # 4. Expand the sparse image into userdata in the background. The verified
    #    recovery write path takes roughly 12 GiB/min on this handset.
    Write-Host "writing userdata (about 10 minutes; do not unplug)..."
    Invoke-AdbShell "nohup simg2img /tmp/samurai-flash.simg /dev/block/by-name/userdata > /tmp/samurai-simg2img.log 2>&1 &" | Out-Null

    $deadline = (Get-Date).AddMinutes(25)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 20
        $state = Invoke-AdbShell "if pgrep -f simg2img >/dev/null 2>&1; then echo RUNNING; else echo DONE; fi"
        if ($state -match 'DONE') { break }
    }
    if ($state -notmatch 'DONE') {
        Invoke-AdbShell "cat /tmp/samurai-simg2img.log" | Write-Host
        throw "simg2img did not finish within 25 minutes"
    }
    Invoke-AdbShell "rm -f /tmp/samurai-flash.simg" | Out-Null
    Write-Host "userdata written." -ForegroundColor Green

    if ($Reboot) {
        Invoke-Adb -Arguments @("reboot") | Out-Null
    } else {
        Write-Host "Now run: adb reboot   (or power-cycle the phone)"
    }
} finally {
    if (Test-Path -LiteralPath $chunkDir) { Remove-Item -LiteralPath $chunkDir -Recurse -Force -ErrorAction SilentlyContinue }
}
