[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\camera-final-boot\boot-eud-production-off.img",
    [int]$WaitSeconds = 0,
    [switch]$Flash
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54"

if (-not (Test-Path -LiteralPath $Fastboot -PathType Leaf)) {
    throw "fastboot not found: $Fastboot"
}
if (-not (Test-Path -LiteralPath $BootImage -PathType Leaf)) {
    throw "boot image not found: $BootImage"
}

$actualHash = (Get-FileHash -LiteralPath $BootImage -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedBootSha256) {
    throw "boot image hash mismatch: expected $ExpectedBootSha256, got $actualHash"
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
Write-Host "boot=$BootImage"
Write-Host "sha256=$actualHash"

if (-not $Flash) {
    Write-Host "dry-run only; pass -Flash to write the boot partition"
    exit 0
}

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

$rebootResult = Invoke-FastbootCapture -Arguments @("-s", $Serial, "reboot")
$rebootResult.Output.Trim() | Write-Host
if ($rebootResult.ExitCode -ne 0) {
    throw "fastboot reboot failed with exit code $($rebootResult.ExitCode)"
}
