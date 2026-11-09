[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\standard-rootfs-candidate\boot-eud-standard-rootfs.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\standard-rootfs-candidate\recovery-kernel-fat.img",
    [int]$WaitSeconds = 0,
    [switch]$FlashBoot,
    [switch]$FlashKernelFat,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "e1cccd9d3d1119c2b40bda4d15834ea857ca8ec897e611f9af28b1e66050bd19"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "8a684871daa9b32d38c0c514e21b7d6b5076a280b35f9ae236821d040ffa46cf"
$ExpectedFatBytes = 67108864

function Verify-Payload {
    param(
        [string]$Path,
        [string]$ExpectedHash,
        [int]$ExpectedBytes
    )
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

Write-Host "standard-rootfs candidate:"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  root=PARTLABEL=userdata rootfstype=f2fs rootwait rw"

if (($FlashBoot -or $FlashKernelFat) -and -not ($FlashBoot -and $FlashKernelFat)) {
    throw "standard-rootfs deployment requires both -FlashBoot and -FlashKernelFat; partial flashing is rejected"
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

if ($FlashBoot) {
    $result = Invoke-FastbootCapture -Arguments @(
        "-s", $Serial, "flash", "boot", $BootImage
    )
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
        throw "fastboot flash boot failed"
    }
}

if ($FlashKernelFat) {
    $result = Invoke-FastbootCapture -Arguments @(
        "-s", $Serial, "flash", "logdump", $KernelFat
    )
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
        throw "fastboot flash logdump failed"
    }
}

if ($Reboot) {
    $result = Invoke-FastbootCapture -Arguments @("-s", $Serial, "reboot")
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0) {
        throw "fastboot reboot failed"
    }
}
