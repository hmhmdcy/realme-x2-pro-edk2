[CmdletBinding()]
param(
    [string]$HostName = "10.42.0.1",
    [string]$User = "root",
    [string]$IdentityFile = "$HOME\.ssh\samurai_id_ed25519",
    [string]$KnownHostsFile = "$HOME\.ssh\samurai_usb_known_hosts",
    [string]$BootImage = "E:\edk2-samurai-out\standard-arm64-v731\thin-private-final-20261109\boot-eud-production-off.img",
    [string]$KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\thin-private-final-20261109\recovery-kernel-fat-thin-private-final.img",
    [string]$Helper = "E:\RealmeX2Pro edk2\linux-port\scripts\flash-pair-linux.sh",
    [int]$WaitSeconds = 120,
    [switch]$FlashBoot,
    [switch]$FlashKernelFat,
    [switch]$Reboot,
    [switch]$Baseline,
    [switch]$KeepPayload
)

$ErrorActionPreference = "Stop"
$ExpectedBootSha256 = "5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf"
$ExpectedBootBytes = 100663296
$ExpectedFatSha256 = "1f4bbb302a62d1f8a950994ac93b00ca194a41c768d4d11b1b97c69f5702574b"
$ExpectedFatBytes = 67108864

if ($Baseline) {
    $BootImage = "E:\edk2-samurai-out\standard-arm64-v731\thin-private-final-20261109\rollback\boot-baseline-5b4dd487.img"
    $KernelFat = "E:\edk2-samurai-out\standard-arm64-v731\thin-private-final-20261109\rollback\recovery-kernel-fat-baseline-c99c690e.img"
    $ExpectedBootSha256 = "5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf"
    $ExpectedFatSha256 = "c99c690ee923238b0954975682c0e40ce99ae63afd048d40b5059fea70e5862e"
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

function Invoke-Native {
    param([string]$FilePath, [string[]]$Arguments)
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $FilePath @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    [pscustomobject]@{ Output = $output; ExitCode = $exitCode }
}

function New-SshArgs {
    param([string[]]$Arguments)
    $result = @(
        "-i", $IdentityFile,
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "UserKnownHostsFile=$KnownHostsFile",
        "-o", "StrictHostKeyChecking=yes",
        "$User@$HostName"
    )
    $result += $Arguments
    return $result
}

function Test-SshReady {
    $result = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @("true"))
    return $result.ExitCode -eq 0
}

if (($FlashBoot -or $FlashKernelFat) -and -not ($FlashBoot -and $FlashKernelFat)) {
    throw "Linux-side deployment requires both -FlashBoot and -FlashKernelFat; partial flashing is rejected"
}
if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "SSH identity not found: $IdentityFile"
}
if (-not (Test-Path -LiteralPath $KnownHostsFile -PathType Leaf)) {
    throw "SSH known-hosts file not found: $KnownHostsFile"
}
if (-not (Test-Path -LiteralPath $Helper -PathType Leaf)) {
    throw "Linux-side flash helper not found: $Helper"
}

$bootHash = Verify-Payload -Path $BootImage -ExpectedHash $ExpectedBootSha256 -ExpectedBytes $ExpectedBootBytes
$fatHash = Verify-Payload -Path $KernelFat -ExpectedHash $ExpectedFatSha256 -ExpectedBytes $ExpectedFatBytes
$helperHash = (Get-FileHash -LiteralPath $Helper -Algorithm SHA256).Hash.ToLowerInvariant()
$pairLabel = if ($Baseline) { "currently deployed rollback pair" } else { "thin-private final pair" }

Write-Host "$pairLabel (Linux-side):"
Write-Host "  boot=$BootImage"
Write-Host "  boot_sha256=$bootHash"
Write-Host "  kernel_fat=$KernelFat"
Write-Host "  kernel_fat_sha256=$fatHash"
Write-Host "  helper=$Helper"
Write-Host "  helper_sha256=$helperHash"
Write-Host "  target=$User@$HostName"

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while (-not (Test-SshReady)) {
    if ($WaitSeconds -le 0 -or (Get-Date) -ge $deadline) {
        throw "SSH target $User@$HostName is not ready"
    }
    Start-Sleep -Seconds 2
}

$runId = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteDir = "/tmp/samurai-pair-$runId"
$remoteBoot = "$remoteDir/boot.img"
$remoteFat = "$remoteDir/kernel-fat.img"
$remoteHelper = "$remoteDir/flash-pair-linux.sh"

$mkdir = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @("mkdir -p '$remoteDir'"))
if ($mkdir.ExitCode -ne 0) {
    throw "remote temporary directory creation failed:`n$($mkdir.Output)"
}

try {
    $scpBase = @(
        "-i", $IdentityFile,
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "UserKnownHostsFile=$KnownHostsFile",
        "-o", "StrictHostKeyChecking=yes"
    )
    foreach ($item in @(
        @($Helper, "${User}@${HostName}:$remoteHelper"),
        @($BootImage, "${User}@${HostName}:$remoteBoot"),
        @($KernelFat, "${User}@${HostName}:$remoteFat")
    )) {
        $copy = Invoke-Native -FilePath "scp" -Arguments ($scpBase + $item)
        if ($copy.ExitCode -ne 0) {
            throw "upload failed for $($item[0]):`n$($copy.Output)"
        }
    }

    $remoteCheck = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @(
        "test `$(sha256sum '$remoteHelper' | cut -d' ' -f1) = '$helperHash'"
    ))
    if ($remoteCheck.ExitCode -ne 0) {
        throw "uploaded helper hash mismatch:`n$($remoteCheck.Output)"
    }

    $flashArgs = @(
        "sh '$remoteHelper'",
        "--boot '$remoteBoot' --boot-sha256 '$bootHash'",
        "--logdump '$remoteFat' --logdump-sha256 '$fatHash'"
    )
    if (-not ($FlashBoot -and $FlashKernelFat)) {
        $flashArgs += "--dry-run"
    }
    $result = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @(
        ($flashArgs -join " ")
    ))
    $result.Output.Trim() | Write-Host
    if ($result.ExitCode -ne 0 -or
        $result.Output -notmatch "(?m)^PASS=(pair-written-and-read-back|preflight-only)\r?$") {
        throw "Linux-side pair operation failed; no reboot was requested"
    }

    if (-not ($FlashBoot -and $FlashKernelFat)) {
        Write-Host "dry-run only; pass -FlashBoot -FlashKernelFat to write the pair"
        return
    }

    if (-not $KeepPayload) {
        $null = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @(
            "rm -rf '$remoteDir'"
        ))
    }

    if ($Reboot) {
        $null = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @(
            "sync; reboot"
        ))
        Write-Host "reboot requested"
    }
}
finally {
    if (-not $KeepPayload -and -not ($FlashBoot -and $FlashKernelFat)) {
        $null = Invoke-Native -FilePath "ssh" -Arguments (New-SshArgs -Arguments @(
            "rm -rf '$remoteDir'"
        ))
    }
}
