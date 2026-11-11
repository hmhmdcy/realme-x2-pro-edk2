[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\boot-eud-production-off.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\logdump-usbwake.img",
    [string]$Sparse = "4M",
    [int]$WaitSeconds = 0,
    [switch]$FlashPair,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "b9e9e53129d7d82401385a6f096af8a260a3b3d9e63d5940f7516424f4e6a438"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "2d91d2eae5a65e0f38509d02e2fcdb89954063fcdbe372e10424f0a54041db94"
$ExpectedFatBytes = 67108864

function Verify-Payload {
    param([string]$Path, [string]$ExpectedHash, [long]$ExpectedBytes)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "payload not found: $Path"
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne $ExpectedBytes) {
        throw "payload size mismatch: $Path expected $ExpectedBytes bytes, got $($item.Length)"
    }
    $actualHash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $ExpectedHash) {
        throw "payload hash mismatch: $Path expected $ExpectedHash, got $actualHash"
    }
    return $actualHash
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
    [pscustomobject]@{ Output = $output; ExitCode = $exitCode }
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

if (-not (Test-Path -LiteralPath $Fastboot -PathType Leaf)) {
    throw "fastboot not found: $Fastboot"
}

$bootHash = Verify-Payload -Path $BootImage -ExpectedHash $ExpectedBootSha256 -ExpectedBytes $ExpectedBootBytes
$fatHash = Verify-Payload -Path $KernelFat -ExpectedHash $ExpectedFatSha256 -ExpectedBytes $ExpectedFatBytes

Write-Host "usbwake final pair:"
Write-Host "  release=7.3.1-rmx1931-samurai-v731-usbwake"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  flash_order=logdump,then boot"

if (-not $FlashPair) {
    Write-Host "dry-run only; pass -FlashPair to deploy both partitions"
    exit 0
}

if ($Reboot -and $WaitSeconds -le 0) {
    throw "-Reboot requires a positive -WaitSeconds so the caller can observe the bootloader transition"
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while (-not (Find-FastbootDevice)) {
    if ($WaitSeconds -le 0 -or (Get-Date) -ge $deadline) {
        throw "fastboot device $Serial is not enumerated"
    }
    Start-Sleep -Seconds 2
}

$product = Invoke-FastbootCapture -Arguments @("-s", $Serial, "getvar", "product")
if ($product.ExitCode -ne 0 -or
    $product.Output -notmatch "product:\s*$([regex]::Escape($ExpectedProduct))") {
    throw "unexpected fastboot product:`n$($product.Output)"
}

$result = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "-S", $Sparse, "flash", "logdump", $KernelFat
)
$result.Output.Trim() | Write-Host
if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot flash logdump failed; boot partition was not touched"
}

$result = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "-S", $Sparse, "flash", "boot", $BootImage
)
$result.Output.Trim() | Write-Host
if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot flash boot failed after logdump succeeded; old boot remains installed"
}

if ($Reboot) {
    $result = Invoke-FastbootCapture -Arguments @("-s", $Serial, "reboot")
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0) {
        throw "fastboot reboot failed"
    }
}
