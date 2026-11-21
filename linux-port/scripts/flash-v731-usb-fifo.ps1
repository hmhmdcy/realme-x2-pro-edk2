[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\usb-fifo-standard-r16-20261108-b\boot-eud-production-off.img",
    [int]$WaitSeconds = 0,
    [switch]$Reboot,
    [switch]$Flash
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "7f8d7a65a3c450fd6abd2a41c5d4e1f359ffe4f7b66a36e53e4ec7aea2782777"
$ExpectedBytes = 100663296

if (-not (Test-Path -LiteralPath $Fastboot -PathType Leaf)) {
    throw "fastboot not found: $Fastboot"
}
if (-not (Test-Path -LiteralPath $BootImage -PathType Leaf)) {
    throw "candidate boot image not found: $BootImage"
}
if ((Get-Item -LiteralPath $BootImage).Length -ne $ExpectedBytes) {
    throw "candidate boot image size mismatch: expected $ExpectedBytes bytes"
}

$actualHash = (Get-FileHash -LiteralPath $BootImage -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedBootSha256) {
    throw "candidate boot hash mismatch: expected $ExpectedBootSha256, got $actualHash"
}

function Invoke-FastbootCapture {
    param([string[]]$Arguments)

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Fastboot @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    [pscustomobject]@{
        Output = $output
        ExitCode = $exitCode
    }
}

function Find-FastbootDevice {
    $lines = (Invoke-FastbootCapture -Arguments @("devices")).Output
    foreach ($line in ($lines -split "`r?`n")) {
        $fields = $line.Trim() -split "\s+"
        if ($fields.Count -ge 2 -and $fields[0] -eq $Serial -and $fields[1] -eq "fastboot") {
            return $true
        }
    }
    return $false
}

if (-not $Flash) {
    Write-Host "candidate boot=$BootImage"
    Write-Host "sha256=$actualHash"
    Write-Host "dry-run only; pass -Flash to write the candidate boot partition"
    exit 0
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while (-not (Find-FastbootDevice)) {
    if ($WaitSeconds -le 0 -or (Get-Date) -ge $deadline) {
        throw "fastboot device $Serial is not enumerated"
    }
    Start-Sleep -Seconds 2
}

$productResult = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "getvar", "product"
)
if ($productResult.ExitCode -ne 0 -or
    $productResult.Output -notmatch "product:\s*$([regex]::Escape($ExpectedProduct))") {
    throw "unexpected fastboot product:`n$($productResult.Output)"
}

Write-Host "device=$Serial product=$ExpectedProduct"
Write-Host "candidate boot=$BootImage"
Write-Host "sha256=$actualHash"
Write-Host "scope=boot only; no NV/persist/logdump/userdata writes"

$flashResult = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "flash", "boot", $BootImage
)
$flashResult.Output.Trim() | Write-Host
if ($flashResult.ExitCode -ne 0) {
    throw "fastboot flash boot failed with exit code $($flashResult.ExitCode)"
}
if ($flashResult.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot did not report a completed write"
}

if ($Reboot) {
    $rebootResult = Invoke-FastbootCapture -Arguments @("-s", $Serial, "reboot")
    $rebootResult.Output.Trim() | Write-Host
    if ($rebootResult.ExitCode -ne 0) {
        throw "fastboot reboot failed with exit code $($rebootResult.ExitCode)"
    }
}
else {
    Write-Host "candidate boot written; reboot manually, then run the NCM matrix"
}
