[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\usb-fifo-standard-r16-20261108-b\boot-eud-production-off.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\usb-fifo-standard-r16-20261108-b\recovery-kernel-fat-fifo.img",
    [int]$WaitSeconds = 0,
    [switch]$FlashBoot,
    [switch]$FlashKernelFat,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "7f8d7a65a3c450fd6abd2a41c5d4e1f359ffe4f7b66a36e53e4ec7aea2782777"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "1f3a40f4e02ae67e2e7ada9029592a539e74be65905a1e54562f68c9e65550c4"
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

Write-Host "USB FIFO standard-rootfs pair:"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  dtb=tx-fifo-resize; root=PARTLABEL=userdata"

if (($FlashBoot -or $FlashKernelFat) -and -not ($FlashBoot -and $FlashKernelFat)) {
    throw "USB FIFO deployment requires both -FlashBoot and -FlashKernelFat; partial flashing is rejected"
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

$result = Invoke-FastbootCapture -Arguments @("-s", $Serial, "flash", "boot", $BootImage)
$result.Output.Trim() | Write-Host
if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot flash boot failed"
}

$result = Invoke-FastbootCapture -Arguments @("-s", $Serial, "flash", "logdump", $KernelFat)
$result.Output.Trim() | Write-Host
if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot flash logdump failed"
}

if ($Reboot) {
    $result = Invoke-FastbootCapture -Arguments @("-s", $Serial, "reboot")
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0) {
        throw "fastboot reboot failed"
    }
}
