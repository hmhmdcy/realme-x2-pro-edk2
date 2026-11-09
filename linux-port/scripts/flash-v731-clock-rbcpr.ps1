[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$ExpectedProduct = "msmnile",
    [string]$Fastboot = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\fastboot.exe",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\clock-rbcpr-candidate\boot-eud-clock-rbcpr.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\clock-rbcpr-candidate\kernel-fat-clock-rbcpr.img",
    [int]$WaitSeconds = 0,
    [switch]$FlashBoot,
    [switch]$FlashKernelFat,
    [switch]$Reboot
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "c5e856d5ac06a42fb55df909dae26fe26293517aa65fd67570730f6de068690c"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "3e788ccbf9fa598f43c25be7747a0571742e21df18b4bb8f5917def2ed65117a"
$ExpectedFatBytes = 67108864

function Verify-Payload {
    param(
        [string]$Path,
        [string]$ExpectedHash,
        [long]$ExpectedBytes
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

Write-Host "clock RBCPR candidate:"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  chain=BDS -> \EFI\BOOT\BOOTAA64.EFI -> GRUB -> /Image + /samurai.dtb"
Write-Host "  cmdline=console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata rootfstype=f2fs rootwait rw"
Write-Host "  safety_flag=absent; expected gcc_cpuss_rbcpr_clk is CLK_IS_CRITICAL"

if (($FlashBoot -or $FlashKernelFat) -and -not ($FlashBoot -and $FlashKernelFat)) {
    throw "clock RBCPR deployment requires both -FlashBoot and -FlashKernelFat; partial flashing is rejected"
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
    "-s", $Serial, "flash", "boot", $BootImage
)
$result.Output.Trim() | Write-Host
if ($result.ExitCode -ne 0 -or $result.Output -notmatch "(?im)^\s*Finished\b") {
    throw "fastboot flash boot failed"
}

$result = Invoke-FastbootCapture -Arguments @(
    "-s", $Serial, "flash", "logdump", $KernelFat
)
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
