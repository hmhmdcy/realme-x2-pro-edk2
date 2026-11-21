[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("insert", "remove")]
    [string]$Mode,

    [string]$Address,

    [string]$Key = "E:\edk2-samurai-out\kernel72\id_ed25519",

    [string]$KnownHosts = "E:\edk2-samurai-out\kernel109\known_hosts-pmos",

    [string]$WorkerPath = (Join-Path $PSScriptRoot "physical_wake_worker.py"),

    [string]$OutputRoot = "E:\edk2-samurai-out\charging-management-20261023",

    [ValidateRange(10, 120)]
    [int]$RemoteCommandTimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

if (-not $Address) {
    $Address = if ($Mode -eq "insert") { "192.168.0.114" } else { "169.254.42.1" }
}
if (-not (Test-Path -LiteralPath $WorkerPath -PathType Leaf)) {
    throw "worker not found: $WorkerPath"
}

$sshOptions = @(
    "-i", $Key,
    "-o", "IdentitiesOnly=yes",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=5",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "UserKnownHostsFile=$KnownHosts"
)
$target = "root@$Address"
$runId = "physical-usb-wake-$Mode-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss'))"
$remote = "/root/charging-management-20261023/$runId"
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

Invoke-Remote "mkdir -p '$remote'" | Out-Null
& scp @sshOptions $WorkerPath "${target}:$remote/worker.py"
if ($LASTEXITCODE -ne 0) {
    throw "worker upload failed"
}
Invoke-Remote "chmod go-w '$remote/worker.py'" | Out-Null

$start = "nohup python3 -B '$remote/worker.py' --root '$remote/evidence' --mode '$Mode' " +
    "> '$remote/worker-stdout.txt' 2> '$remote/worker-stderr.txt' & echo `$!"
$launch = Invoke-Remote $start
$launch.Output | Set-Content -LiteralPath (Join-Path $local "launch.txt") -Encoding utf8

$ready = $null
$deadline = [DateTime]::UtcNow.AddSeconds(60)
while ([DateTime]::UtcNow -lt $deadline) {
    $reply = Invoke-Remote "cat '$remote/evidence/ready.json' 2>/dev/null" -AllowFailure
    if ($reply.Code -eq 0) {
        try {
            $ready = ($reply.Output -join "`n") | ConvertFrom-Json
            break
        } catch {
            # The file can be between rename and visibility on the SSH overlay.
        }
    }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    throw "device worker did not become ready; inspect $remote/worker-stderr.txt"
}

$readyJson = $ready | ConvertTo-Json -Depth 8
$readyJson | Set-Content -LiteralPath (Join-Path $local "ready.json") -Encoding utf8
Write-Host "Run: $runId"
Write-Host "Mode: $Mode"
Write-Host "Boot: $($ready.boot_id)"
Write-Host "Owned IRQs: $($ready.event_irqs | ConvertTo-Json -Compress)"
Write-Host "RTC safety fallback: $($ready.alarm_seconds)s (never an acceptance result)"
Write-Host ""

if ($Mode -eq "insert") {
    Write-Host "Keep the USB data cable DISCONNECTED before continuing."
    Write-Host "After Enter, suspend begins in $($ready.pre_suspend_delay_seconds) seconds."
    Write-Host "About 25 seconds from now, insert the cable exactly once."
    Write-Host "Do not press power or volume keys. Do not use an RTC alarm."
} else {
    Write-Host "Keep the USB data cable CONNECTED and NCM healthy before continuing."
    Write-Host "After Enter, suspend begins in $($ready.pre_suspend_delay_seconds) seconds."
    Write-Host "About 25 seconds from now, remove the cable exactly once."
    Write-Host "Do not press power or volume keys. Do not use an RTC alarm."
}
[void](Read-Host "Press Enter only when the physical setup matches the instruction")

$go = @{ boot_id = $ready.boot_id } | ConvertTo-Json -Compress
$goRemote = $go.Replace("'", "'\''")
Invoke-Remote "printf '%s\n' '$goRemote' > '$remote/evidence/go.json'" | Out-Null
Write-Host "GO. Perform the instructed USB action about 25 seconds from now."

$result = $null
$terminal = $null
$deadline = [DateTime]::UtcNow.AddSeconds(260)
while ([DateTime]::UtcNow -lt $deadline) {
    $reply = Invoke-Remote "cat '$remote/evidence/terminal.json' 2>/dev/null" -AllowFailure
    if ($reply.Code -eq 0) {
        try {
            $terminal = ($reply.Output -join "`n") | ConvertFrom-Json
            break
        } catch {
            # Retry while the device is suspended or the file is incomplete.
        }
    }
    Start-Sleep -Seconds 4
}
if (-not $terminal) {
    throw "wake test did not reach a terminal state; inspect $remote"
}

$fetch = "cat '$remote/evidence/result.json' '$remote/evidence/failure.json' 2>/dev/null"
$reply = Invoke-Remote $fetch -AllowFailure
$reply.Output | Set-Content -LiteralPath (Join-Path $local "result-or-failure.txt") -Encoding utf8

& scp @sshOptions "${target}:$remote/evidence/*.json" $local
$scpCode = $LASTEXITCODE
if ($scpCode -ne 0) {
    Write-Warning "some evidence files could not be copied; remote copy remains at $remote"
}

$resultPath = Join-Path $local "result.json"
if (Test-Path -LiteralPath $resultPath) {
    $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    $summary = [ordered]@{
        accepted = $result.accepted
        mode = $result.mode
        boot_id = $result.boot_id
        same_boot = $result.same_boot
        residency_seconds = $result.estimated_residency_seconds
        suspend_stats_delta = $result.suspend_stats_delta
        event_irq_deltas = $result.event_irq_deltas
        rtc_irq_delta = $result.rtc_irq_delta
        pm_wakeup_irq = $result.pm_wakeup_irq
        pm_wakeup_irq_is_owned_event = $result.pm_wakeup_irq_is_owned_event
        errors = @($result.errors)
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $local "summary.json") -Encoding utf8
    Write-Host ($summary | ConvertTo-Json -Depth 8)
    if (-not $result.accepted) {
        exit 1
    }
} else {
    Write-Warning "no result.json; failure evidence is in $local"
    exit 1
}
