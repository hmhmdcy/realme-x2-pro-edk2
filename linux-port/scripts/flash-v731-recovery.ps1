[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$RecoveryImage = "E:\edk2-samurai-out\standard-arm64-v731\camera-final-boot\recovery-kernel-fat.img",
    [int]$WaitSeconds = 0,
    [switch]$Reboot,
    [switch]$Flash
)

$ErrorActionPreference = "Stop"
$ExpectedRecoverySha256 = "6a6aa520e4adda750450c3fd9b80a553c1988d6d76803c674c279b3a5df4f562"
$ExpectedBytes = 67108864

if (-not (Test-Path -LiteralPath $Fastboot -PathType Leaf)) {
    throw "fastboot not found: $Fastboot"
}
if (-not (Test-Path -LiteralPath $RecoveryImage -PathType Leaf)) {
    throw "recovery image not found: $RecoveryImage"
}
if ((Get-Item -LiteralPath $RecoveryImage).Length -ne $ExpectedBytes) {
    throw "recovery image size mismatch: expected $ExpectedBytes bytes"
}

$actualHash = (Get-FileHash -LiteralPath $RecoveryImage -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedRecoverySha256) {
    throw "recovery image hash mismatch: expected $ExpectedRecoverySha256, got $actualHash"
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
Write-Host "partition=logdump (KERNEL FAT: /Image and /samurai.dtb)"
Write-Host "recovery=$RecoveryImage"
Write-Host "sha256=$actualHash"

if (-not $Flash) {
    Write-Host "dry-run only; pass -Flash to replace the KERNEL FAT"
    exit 0
}

$flashResult = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "flash", "logdump", $RecoveryImage
)
$flashResult.Output.Trim() | Write-Host
if ($flashResult.ExitCode -ne 0) {
    throw "fastboot flash logdump failed with exit code $($flashResult.ExitCode)"
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
