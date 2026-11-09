[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\flash-led-candidate-20261109\boot-build-2\boot-eud-production-off.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\flash-led-candidate-20261109\recovery-kernel-fat-flash-led.img",
    [string]$Sparse = "4M",
    [int]$WaitSeconds = 0,
    [switch]$FlashBoot,
    [switch]$FlashKernelFat,
    [switch]$Reboot,
    [switch]$Baseline
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "9196b22ce55bf7459c95576c85e33280bd9b1452f983dac20dbefd6047a541f0"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "74804f420a4969da99e123ec6eb48c7834e7c074fbb0609bb52aa5dca2750cd2"
$ExpectedFatBytes = 67108864

if ($Baseline) {
    $BootImage = "E:\edk2-samurai-out\standard-arm64-v731\flash-led-candidate-20261109\rollback\boot-baseline-9b9be136.img"
    $KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\flash-led-candidate-20261109\rollback\recovery-kernel-fat-baseline.img"
    $ExpectedBootSha256 = "9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54"
    $ExpectedFatSha256 = "6a6aa520e4adda750450c3fd9b80a553c1988d6d76803c674c279b3a5df4f562"
}

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

$pairLabel = if ($Baseline) { "known-good baseline pair" } else { "Flash-LED candidate pair" }
Write-Host "$pairLabel`:"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  fastboot_sparse_chunk=$Sparse"
if (-not $Baseline) {
    Write-Host "  dtb=pm8150l flash channels 1+2, standard LED-flash/V4L2-flash"
}

if (($FlashBoot -or $FlashKernelFat) -and -not ($FlashBoot -and $FlashKernelFat)) {
    throw "Flash-LED deployment requires both -FlashBoot and -FlashKernelFat; partial flashing is rejected"
}

if (-not $FlashBoot -and -not $FlashKernelFat) {
    Write-Host "dry-run only; pass -FlashBoot -FlashKernelFat to deploy the pair"
    exit 0
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
