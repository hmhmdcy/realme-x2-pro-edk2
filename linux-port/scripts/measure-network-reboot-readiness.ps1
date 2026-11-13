#!/usr/bin/env pwsh
<#
.SYNOPSIS
Measure Wi-Fi and USB NCM SSH readiness across one ordinary reboot.

.DESCRIPTION
The script records the old boot identity, requests a normal reboot over the
Wi-Fi SSH control path, then polls TCP/22 and strict-key SSH on both the Wi-Fi
and USB NCM endpoints. It is read-only apart from the reboot, never flashes a
partition, and writes the observed readiness timeline as JSON.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$Identity,

    [Parameter(Mandatory = $true)]
    [string]$KnownHosts,

    [string]$WifiHost = "192.168.0.114",
    [string]$NcmHost = "172.16.42.1",
    [string]$NcmBindAddress = "172.16.42.2",
    [string]$NcmKnownHosts,
    [string]$User = "root",
    [ValidateRange(60, 900)]
    [int]$TimeoutSeconds = 360,
    [int]$ConnectTimeoutSeconds = 3,
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-DeviceSsh {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][string]$Command,
        [string]$HostsFile = $KnownHosts,
        [string[]]$ExtraArgs = @()
    )

    $sshArgs = @(
        "-F", "none",
        "-i", $Identity,
        "-o", "IdentitiesOnly=yes",
        "-o", "PasswordAuthentication=no",
        "-o", "UserKnownHostsFile=$HostsFile",
        "-o", "GlobalKnownHostsFile=none",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=$ConnectTimeoutSeconds",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=2",
        "-o", "LogLevel=ERROR"
    )
    if ($ExtraArgs.Count -ne 0) {
        $sshArgs += $ExtraArgs
    }
    $sshArgs += "$User@$HostName"
    $sshArgs += $Command

    $output = & ssh @sshArgs 2>&1
    $exitCode = $LASTEXITCODE
    [pscustomobject]@{
        exit_code = $exitCode
        output = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
    }
}

function Test-Tcp22 {
    param([Parameter(Mandatory = $true)][string]$HostName)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, 22)
        if ($task.Wait(1000) -and $client.Connected) {
            return $true
        }
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
    return $false
}

function Get-DeviceIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [string]$HostsFile = $KnownHosts,
        [string[]]$ExtraArgs = @()
    )

    $result = Invoke-DeviceSsh -HostName $HostName -HostsFile $HostsFile `
        -ExtraArgs $ExtraArgs -Command @'
cat /proc/sys/kernel/random/boot_id
grep '^btime ' /proc/stat
date +%s
cut -d. -f1 /proc/uptime
'@
    if ($result.exit_code -ne 0) {
        return $null
    }

    $lines = @($result.output -split "`r?`n")
    if ($lines.Count -lt 4) {
        return $null
    }
    $bootFields = $lines[1] -split "\s+"
    if ($bootFields.Count -ne 2) {
        return $null
    }

    [pscustomobject]@{
        boot_id = $lines[0]
        btime_epoch = [int64]$bootFields[1]
        device_epoch = [int64]$lines[2]
        uptime_seconds = [int64]$lines[3]
        btime_plausible = (
            [int64]$bootFields[1] -ge
            [DateTimeOffset]::new(2020, 1, 1, 0, 0, 0, [TimeSpan]::Zero).ToUnixTimeSeconds()
        )
    }
}

function Get-NcmHostState {
    $adapter = Get-NetAdapter -ErrorAction SilentlyContinue |
        Where-Object {
            $_.InterfaceDescription -match "^UsbNcm" -and
            $_.Status -eq "Up"
        } |
        Sort-Object ifIndex -Descending |
        Select-Object -First 1

    if ($null -eq $adapter) {
        return $null
    }

    $pnpArrival = $null
    $pnpDevice = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -like "USB\VID_0525&PID_A4A1&MI_00*" } |
        Select-Object -First 1
    if ($null -ne $pnpDevice) {
        try {
            $pnpArrival = (Get-PnpDeviceProperty `
                -InstanceId $pnpDevice.InstanceId `
                -KeyName "DEVPKEY_Device_LastArrivalDate" `
                -ErrorAction Stop).Data
        }
        catch {
            $pnpArrival = $null
        }
    }

    $leaseObtained = $null
    $leaseExpires = $null
    $interfaceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\$($adapter.InterfaceGuid)"
    if (Test-Path $interfaceKey) {
        $ip = Get-ItemProperty -Path $interfaceKey
        if ($null -ne $ip.LeaseObtainedTime) {
            $leaseObtained = [DateTimeOffset]::FromUnixTimeSeconds(
                [int64]$ip.LeaseObtainedTime
            ).ToLocalTime()
        }
        if ($null -ne $ip.LeaseTerminatesTime) {
            $leaseExpires = [DateTimeOffset]::FromUnixTimeSeconds(
                [int64]$ip.LeaseTerminatesTime
            ).ToLocalTime()
        }
    }

    [pscustomobject]@{
        adapter_name = $adapter.Name
        interface_index = $adapter.ifIndex
        interface_guid = $adapter.InterfaceGuid
        status = $adapter.Status
        link_speed = $adapter.LinkSpeed
        pnp_last_arrival = $pnpArrival
        dhcp_lease_obtained = $leaseObtained
        dhcp_lease_expires = $leaseExpires
    }
}

if (-not (Test-Path -LiteralPath $Identity -PathType Leaf)) {
    throw "SSH identity not found: $Identity"
}
if (-not (Test-Path -LiteralPath $KnownHosts -PathType Leaf)) {
    throw "known_hosts not found: $KnownHosts"
}
$ncmHostsFile = if ($NcmKnownHosts) { $NcmKnownHosts } else { $KnownHosts }
if (-not (Test-Path -LiteralPath $ncmHostsFile -PathType Leaf)) {
    throw "NCM known_hosts not found: $ncmHostsFile"
}
$ncmSshArgs = @(
    "-b", $NcmBindAddress,
    "-o", "ProxyCommand=none",
    "-o", "ProxyJump=none"
)

$oldIdentity = Get-DeviceIdentity -HostName $WifiHost
if ($null -eq $oldIdentity) {
    $oldIdentity = Get-DeviceIdentity -HostName $NcmHost `
        -HostsFile $ncmHostsFile -ExtraArgs $ncmSshArgs
}
if ($null -eq $oldIdentity) {
    throw "Neither Wi-Fi nor USB NCM SSH is reachable before reboot"
}

$hostBefore = Get-NcmHostState
$result = [ordered]@{
    schema = "samurai-network-reboot-readiness-v1"
    started_local = [DateTimeOffset]::Now.ToString("o")
    old_device = $oldIdentity
    host_before = $hostBefore
    addresses = [ordered]@{
        wifi = $WifiHost
        ncm = $NcmHost
        ncm_bind = $NcmBindAddress
    }
    wifi = [ordered]@{}
    ncm = [ordered]@{}
    new_device = $null
    passed = $false
}

if (-not $PSCmdlet.ShouldProcess(
        "$WifiHost",
        "Reboot the handset once and measure network readiness"
    )) {
    $result | ConvertTo-Json -Depth 8
    return
}

$start = [DateTimeOffset]::Now
$result.reboot_requested_local = $start.ToString("o")
$reboot = Invoke-DeviceSsh -HostName $WifiHost -Command @'
sync
nohup sh -c 'sleep 2; reboot' >/dev/null 2>&1 &
'@
$result.reboot_command_exit_code = $reboot.exit_code

$wifiTcpAt = $null
$ncmTcpAt = $null
$wifiSshAt = $null
$ncmSshAt = $null
$wifiDownSeen = $false
$ncmDownSeen = $false
$wifiIdentityAfter = $null
$ncmIdentityAfter = $null
$newIdentity = $null
$deadline = $start.AddSeconds($TimeoutSeconds)

while ([DateTimeOffset]::Now -lt $deadline) {
    $now = [DateTimeOffset]::Now

    $wifiOpen = Test-Tcp22 -HostName $WifiHost
    if (-not $wifiOpen) {
        $wifiDownSeen = $true
    }
    elseif ($null -eq $wifiIdentityAfter) {
        $candidate = Get-DeviceIdentity -HostName $WifiHost
        if (
            $null -ne $candidate -and
            $candidate.boot_id -ne $oldIdentity.boot_id -and
            (
                $null -eq $newIdentity -or
                $candidate.boot_id -eq $newIdentity.boot_id
            )
        ) {
            $wifiIdentityAfter = $candidate
            $wifiSshAt = $now
            if ($null -eq $wifiTcpAt) {
                $wifiTcpAt = $now
            }
            if ($null -eq $newIdentity) {
                $newIdentity = $candidate
            }
        }
    }

    $ncmOpen = Test-Tcp22 -HostName $NcmHost
    if (-not $ncmOpen) {
        $ncmDownSeen = $true
    }
    elseif ($null -eq $ncmIdentityAfter) {
        $candidate = Get-DeviceIdentity -HostName $NcmHost `
            -HostsFile $ncmHostsFile -ExtraArgs $ncmSshArgs
        if (
            $null -ne $candidate -and
            $candidate.boot_id -ne $oldIdentity.boot_id -and
            (
                $null -eq $newIdentity -or
                $candidate.boot_id -eq $newIdentity.boot_id
            )
        ) {
            $ncmIdentityAfter = $candidate
            $ncmSshAt = $now
            if ($null -eq $ncmTcpAt) {
                $ncmTcpAt = $now
            }
            if ($null -eq $newIdentity) {
                $newIdentity = $candidate
            }
        }
    }

    if ($null -ne $wifiSshAt -and $null -ne $ncmSshAt) {
        break
    }
    Start-Sleep -Seconds 1
}

$result.finished_local = [DateTimeOffset]::Now.ToString("o")
$result.new_device = $newIdentity
$result.host_after = Get-NcmHostState

function Add-Timing {
    param(
        [System.Collections.Specialized.OrderedDictionary]$Target,
        [string]$Name,
        $Timestamp
    )
    if ($null -eq $Timestamp) {
        $Target[$Name] = $null
        return
    }
    $offset = [math]::Round(($Timestamp - $start).TotalSeconds, 3)
    $Target[$Name] = [ordered]@{
        local = $Timestamp.ToString("o")
        seconds_after_request = $offset
    }
}

Add-Timing -Target $result.wifi -Name "tcp22_ready" -Timestamp $wifiTcpAt
Add-Timing -Target $result.wifi -Name "ssh_new_boot_ready" -Timestamp $wifiSshAt
Add-Timing -Target $result.ncm -Name "tcp22_ready" -Timestamp $ncmTcpAt
Add-Timing -Target $result.ncm -Name "ssh_new_boot_ready" -Timestamp $ncmSshAt
$result.wifi.old_tcp22_dropped = $wifiDownSeen
$result.ncm.old_tcp22_dropped = $ncmDownSeen

if ($null -ne $wifiIdentityAfter) {
    $result.wifi.device_identity = $wifiIdentityAfter
}
if ($null -ne $ncmIdentityAfter) {
    $result.ncm.device_identity = $ncmIdentityAfter
}

$result.passed = (
    $null -ne $newIdentity -and
    $null -ne $wifiIdentityAfter -and
    $null -ne $ncmIdentityAfter -and
    $null -ne $wifiSshAt -and
    $null -ne $ncmSshAt -and
    $wifiIdentityAfter.boot_id -eq $ncmIdentityAfter.boot_id -and
    $newIdentity.boot_id -ne $oldIdentity.boot_id
)

$rendered = $result | ConvertTo-Json -Depth 8
if ($OutputPath) {
    $parent = Split-Path -Parent $OutputPath
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $rendered -Encoding utf8
}
$rendered
if (-not $result.passed) {
    exit 1
}
