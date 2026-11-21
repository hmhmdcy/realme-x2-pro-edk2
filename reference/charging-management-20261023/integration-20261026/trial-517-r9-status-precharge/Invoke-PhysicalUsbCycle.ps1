#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$Address = "192.168.0.114",

    [string]$Key = "E:\edk2-samurai-out\kernel72\id_ed25519",

    [string]$KnownHosts = "E:\edk2-samurai-out\kernel109\known_hosts-pmos",

    [string]$WorkerPath,

    [string]$OutputRoot = "E:\edk2-samurai-out\charging-management-20261023",

    [ValidateRange(30, 300)]
    [int]$ReadyTimeoutSeconds = 90,

    [ValidateRange(30, 300)]
    [int]$DetachTimeoutSeconds = 120,

    [ValidateRange(60, 600)]
    [int]$TerminalTimeoutSeconds = 300,

    [ValidateRange(10, 120)]
    [int]$RemoteCommandTimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

if (-not $WorkerPath) {
    $WorkerPath = Join-Path $PSScriptRoot "physical_cycle_worker.py"
}

if ($Address -match '^169\.254\.') {
    throw (
        "Physical USB cycles cannot use an NCM link-local address for control: " +
        "unplugging the cable also removes that SSH path. Use the phone's Wi-Fi " +
        "address so the host can observe detach evidence before asking you to reconnect."
    )
}
if (-not (Test-Path -LiteralPath $WorkerPath -PathType Leaf)) {
    throw "worker not found: $WorkerPath"
}
if (-not (Test-Path -LiteralPath $Key -PathType Leaf)) {
    throw "SSH key not found: $Key"
}
if (-not (Test-Path -LiteralPath $KnownHosts -PathType Leaf)) {
    throw "known_hosts not found: $KnownHosts"
}

$sshOptions = @(
    "-i", $Key,
    "-o", "IdentitiesOnly=yes",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=5",
    "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=2",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "UserKnownHostsFile=$KnownHosts"
)
$target = "root@$Address"
$suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
$runId = "physical-usb-cycle-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss'))-$suffix"
$remoteBase = "/root/charging-management-20261023"
$remote = "$remoteBase/$runId"
$evidence = "$remote/evidence"
$remoteWorker = "$remoteBase/physical-usb-cycle-worker.py"
$local = Join-Path $OutputRoot $runId
New-Item -ItemType Directory -Path $local -Force | Out-Null
$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source

function Invoke-Remote {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [switch]$AllowFailure
    )
    $tempBase = Join-Path $local (
        ".ssh-" + [guid]::NewGuid().ToString("N")
    )
    $stdoutPath = $tempBase + ".out"
    $stderrPath = $tempBase + ".err"
    $code = $null
    $output = @()
    try {
        $process = Start-Process `
            -FilePath $ssh `
            -ArgumentList @($sshOptions + @($target, $Command)) `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -WindowStyle Hidden `
            -PassThru
        if (-not $process.WaitForExit($RemoteCommandTimeoutSeconds * 1000)) {
            try {
                $process.Kill()
                $process.WaitForExit(5000) | Out-Null
            } catch {
            }
            $code = 124
            $output = @("ssh command timed out after $RemoteCommandTimeoutSeconds seconds")
        } else {
            $code = $process.ExitCode
            if (Test-Path -LiteralPath $stdoutPath) {
                $output += @(Get-Content -LiteralPath $stdoutPath)
            }
            if (Test-Path -LiteralPath $stderrPath) {
                $output += @(Get-Content -LiteralPath $stderrPath)
            }
        }
    } catch {
        $code = 125
        $output = @("$($_.Exception.Message)")
    } finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    }
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "ssh failed ($code): $($output -join "`n")"
    }
    return [pscustomobject]@{ Code = $code; Output = @($output) }
}

function Get-RemoteJson {
    param([Parameter(Mandatory = $true)][string]$Path)
    $reply = Invoke-Remote "test -s '$Path' && cat '$Path'" -AllowFailure
    if ($reply.Code -ne 0) {
        return $null
    }
    try {
        return ($reply.Output -join "`n") | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-RemoteSamples {
    $reply = Invoke-Remote "test -s '$evidence/samples.jsonl' && cat '$evidence/samples.jsonl'" -AllowFailure
    if ($reply.Code -ne 0) {
        return @()
    }
    $rows = @()
    foreach ($line in $reply.Output) {
        $text = "$line".Trim()
        if (-not $text) {
            continue
        }
        try {
            $rows += $text | ConvertFrom-Json
        } catch {
            # A concurrently appended final line is retried on the next poll.
        }
    }
    return $rows
}

function Test-DetachedSample {
    param([Parameter(Mandatory = $true)]$Sample)
    if ($Sample.source_online -ne "0") {
        return $false
    }
    $telemetry = $Sample.telemetry
    if ($telemetry.valid -ne 1 -or $telemetry.online -ne 0 -or $telemetry.desired_enable -ne 0) {
        return $false
    }
    foreach ($name in @("error", "stop_error", "latched", "source_inhibit", "fault")) {
        if ($telemetry.$name -ne 0) {
            return $false
        }
    }
    return $true
}

function Write-RemoteText {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )
    $base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Text))
    Invoke-Remote "printf '%s' '$base64' | base64 -d > '$Path'" | Out-Null
}

function Copy-RemoteEvidence {
    param([string[]]$Names)
    $missing = @()
    foreach ($name in $Names) {
        & scp @sshOptions "${target}:$evidence/$name" $local 2>$null
        if ($LASTEXITCODE -ne 0) {
            $missing += $name
        }
    }
    return $missing
}

Write-Host "Run: $runId"
Write-Host "Control: Wi-Fi $Address (NCM control is intentionally rejected)"
Write-Host "Evidence: $local"

Invoke-Remote "mkdir -p '$remote' && chmod 700 '$remoteBase' '$remote'" | Out-Null

$localWorkerHash = (Get-FileHash -LiteralPath $WorkerPath -Algorithm SHA256).Hash.ToLowerInvariant()
$remoteHashReply = Invoke-Remote "sha256sum '$remoteWorker' 2>/dev/null | cut -d' ' -f1" -AllowFailure
$remoteWorkerHash = ($remoteHashReply.Output -join "").Trim().ToLowerInvariant()
if ($remoteHashReply.Code -ne 0 -or $remoteWorkerHash -ne $localWorkerHash) {
    $uploadPath = "$remoteWorker.upload"
    & scp @sshOptions $WorkerPath "${target}:$uploadPath"
    if ($LASTEXITCODE -ne 0) {
        throw "worker upload failed"
    }
    Invoke-Remote "chmod 700 '$uploadPath' && mv '$uploadPath' '$remoteWorker'" | Out-Null
}

$start = "nohup python3 -B '$remoteWorker' --root '$evidence' " +
    "--timeout $TerminalTimeoutSeconds > '$remote/worker-stdout.txt' " +
    "2> '$remote/worker-stderr.txt' & echo `$!"
$launch = Invoke-Remote $start
$launch.Output | Set-Content -LiteralPath (Join-Path $local "launch.txt") -Encoding utf8

$ready = $null
$readyDeadline = [DateTime]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
while ([DateTime]::UtcNow -lt $readyDeadline) {
    $ready = Get-RemoteJson "$evidence/ready.json"
    if ($ready) {
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $ready -or -not $ready.boot_id) {
    throw "device worker did not become ready; inspect $remote/worker-stderr.txt"
}

$readyJson = $ready | ConvertTo-Json -Depth 8
$readyJson | Set-Content -LiteralPath (Join-Path $local "ready.json") -Encoding utf8
Write-Host "Boot: $($ready.boot_id)"
Write-Host "Manifest: $($ready.manifest_sha256)"
Write-Host ""
Write-Host "The phone must be connected, charging, and healthy before the cycle starts."
Write-Host "The worker creates go.json only after the next prompt. Its go window is 120 seconds."
Write-Host "Do not reboot the phone or change charger settings during this test."
[void](Read-Host "Press Enter only when ready; then physically unplug the USB cable")

$go = @{ boot_id = $ready.boot_id } | ConvertTo-Json -Compress
Write-RemoteText "$evidence/go.json" ($go + "`n")
Write-Host "GO. Unplug the USB cable now and keep it detached for at least 2 seconds."

$detachObserved = $null
$detachDeadline = [DateTime]::UtcNow.AddSeconds($DetachTimeoutSeconds)
while ([DateTime]::UtcNow -lt $detachDeadline) {
    $rows = @(Get-RemoteSamples)
    $detachedRows = @($rows | Where-Object { Test-DetachedSample -Sample $_ })
    if ($detachedRows.Count -ge 3) {
        $detachedSpan = [double]$detachedRows[-1].boottime - [double]$detachedRows[0].boottime
        if ($detachedSpan -ge 2.0) {
            $detachObserved = [ordered]@{
                samples = $detachedRows.Count
                span_seconds = $detachedSpan
                first = $detachedRows[0]
                last = $detachedRows[-1]
            }
            break
        }
    }
    Start-Sleep -Seconds 2
}
if (-not $detachObserved) {
    throw (
        "no detached sample was observed before the timeout. The worker and remote " +
        "evidence remain at $remote; do not treat the SSH check as cycle success."
    )
}
$detachObserved | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath (Join-Path $local "detach-observed.json") -Encoding utf8
Write-Host (
    "Detach confirmed by $($detachObserved.samples) device telemetry samples " +
    "over $([math]::Round($detachObserved.span_seconds, 3)) seconds."
)

[void](Read-Host "Reconnect the USB cable now, then press Enter")
Write-Host "Waiting for 15 healthy recovery samples over at least 14 seconds..."

$terminal = $null
$terminalDeadline = [DateTime]::UtcNow.AddSeconds($TerminalTimeoutSeconds)
while ([DateTime]::UtcNow -lt $terminalDeadline) {
    $terminal = Get-RemoteJson "$evidence/terminal.json"
    if ($terminal) {
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $terminal) {
    throw "worker did not reach terminal.json; evidence remains at $remote"
}

$missing = @(Copy-RemoteEvidence @(
    "ready.json",
    "go.json",
    "terminal.json",
    "result.json",
    "failure.json",
    "samples.jsonl"
))
$missing | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $local "missing-evidence.json") -Encoding utf8

$resultPath = Join-Path $local "result.json"
$samplesPath = Join-Path $local "samples.jsonl"
$failurePath = Join-Path $local "failure.json"
if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
    Write-Warning "No result.json was fetched; see $failurePath and $remote"
    exit 1
}
if (-not (Test-Path -LiteralPath $samplesPath -PathType Leaf)) {
    Write-Warning "samples.jsonl was not fetched; acceptance cannot be audited locally"
    exit 1
}

$result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
$localSampleCount = @(
    Get-Content -LiteralPath $samplesPath |
        Where-Object { $_.Trim().Length -gt 0 }
).Count
if ($localSampleCount -lt [int]$result.samples) {
    Write-Warning (
        "samples.jsonl is incomplete locally: fetched $localSampleCount rows, " +
        "result declares $($result.samples)"
    )
    exit 1
}
$summary = [ordered]@{
    accepted = [bool]$result.accepted
    physical_usb_cycle_proven = [bool]$result.physical_usb_cycle_proven
    same_boot = [bool]$result.same_boot
    manifest_unchanged = [bool]$result.manifest_unchanged
    baseline_samples = $result.baseline_samples
    detached_samples = $result.detached_samples
    detached_span_seconds = $result.detached_span_seconds
    recovered_samples = $result.recovered_samples
    recovered_span_seconds = $result.recovered_span_seconds
    local_sample_rows = $localSampleCount
    new_session = [bool]$result.new_session
    after_full_hold = [bool]$result.after_full_hold
    checks = $result.checks
    critical_log_delta = @($result.critical_log_delta)
}
$summary | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $local "summary.json") -Encoding utf8
Write-Host ($summary | ConvertTo-Json -Depth 8)

if (
    $result.accepted -ne $true -or
    $result.physical_usb_cycle_proven -ne $true -or
    $terminal.accepted -ne $true
) {
    exit 1
}

Write-Host "Physical USB detach/reconnect cycle accepted on boot $($ready.boot_id)."
