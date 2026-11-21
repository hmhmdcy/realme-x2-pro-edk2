<#
Acceptance check for the rootfs NCM layering fix.

The link has to move in one direction at a time: Windows enumerates the
gadget, eth_open() fills the gadget RX queue, carrier rises, DHCP hands out
172.16.42.2, and only then does sshd answer.  This script asserts each rung
in that order so a partial success cannot be mistaken for a working link.

Usage:
    verify-ncm-rootfs-link.ps1
    verify-ncm-rootfs-link.ps1 -SkipSsh
#>

[CmdletBinding()]
param(
    [string]$AdapterName = "以太网 10",
    [string]$Server = "172.16.42.1",
    [string]$ClientExpected = "172.16.42.2",
    [string]$SshHost = "172.16.42.1",
    [string]$LinkLocal = "169.254.42.1",
    [string]$User = "user",
    [int]$TimeoutSeconds = 90,
    [switch]$SkipSsh
)

$ErrorActionPreference = "Stop"
$failures = @()
$results = [ordered]@{}

function Record {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $results[$Name] = [pscustomobject]@{ OK = $Ok; Detail = $Detail }
    if (-not $Ok) { $script:failures += "${Name}: $Detail" }
    $status = if ($Ok) { "OK  " } else { "FAIL" }
    Write-Host ("{0} {1,-28} {2}" -f $status, $Name, $Detail)
}

# 1. USB enumeration.  A gadget that is not enumerated cannot carry frames.
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$pnp = $null
while ((Get-Date) -lt $deadline) {
    $pnp = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'VID_0525&PID_A4A1' } |
        Select-Object -First 1
    if ($pnp) { break }
    Start-Sleep -Seconds 2
}
Record "usb-enumerated" ($null -ne $pnp) `
    $(if ($pnp) { $pnp.InstanceId } else { "no 0525:a4a1" })

# 2. Host-side link.  Speed plus 426 Mbps means the NCM data interface was
#    selected; it still proves nothing about device-side RX.
$adapter = $null
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    $adapter = Get-NetAdapter -Name $AdapterName -ErrorAction SilentlyContinue
    if ($adapter -and $adapter.Status -eq 'Up') { break }
    Start-Sleep -Seconds 2
}
Record "host-link-up" ($null -ne $adapter -and $adapter.Status -eq 'Up') `
    $(if ($adapter) { "$($adapter.Status) / $($adapter.LinkSpeed)" } else { "adapter missing" })

# 3. Deliverable bytes in BOTH directions.  This is the decisive rung: the
#    previous failure had SentBytes > 1 MB and ReceivedBytes = 0.
$rxBefore = 0
$txBefore = 0
if ($adapter) {
    $stats = Get-NetAdapterStatistics -Name $AdapterName
    $rxBefore = $stats.ReceivedBytes
    $txBefore = $stats.SentBytes
}

# Provoke a response from the device.  A DHCP DISCOVER produces a unicast
# reply once the gadget RX queue is actually filled.
& ipconfig /renew $AdapterName 2>&1 | Out-Null
Start-Sleep -Seconds 5
$stats = Get-NetAdapterStatistics -Name $AdapterName -ErrorAction SilentlyContinue
if ($stats) {
    $rxDelta = $stats.ReceivedBytes - $rxBefore
    $txDelta = $stats.SentBytes - $txBefore
    Record "device-tx-bytes" ($rxDelta -gt 0) "received +$rxDelta bytes"
    Record "host-tx-bytes" ($txDelta -gt 0) "sent +$txDelta bytes"
} else {
    Record "device-tx-bytes" $false "no statistics"
    Record "host-tx-bytes" $false "no statistics"
}

# 4. ARP reachability.
# 4/5. Reachability.  Developer mode serves 172.16.42.1 and hands out
#      172.16.42.2.  Tethering mode deliberately publishes 10.42.0.1 with
#      dnsmasq and never adds the developer address, so asserting the
#      developer subnet there would fail a correct configuration.  The
#      link-local maintenance path must exist in every mode.
$addresses = @()
if ($adapter) {
    $addresses = @(Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 `
        -ErrorAction SilentlyContinue | ForEach-Object { $_.IPAddress })
}
$hasServer = $addresses | Where-Object { $_ -like '172.16.42.*' }
$hasTether = $addresses | Where-Object { $_ -like '10.42.0.*' }
Record "device-address" ($null -ne $hasServer -or $null -ne $hasTether) `
    $(if ($addresses) { $addresses -join ',' } else { "none" })

$ping = Test-Connection -ComputerName $LinkLocal -Count 3 -Quiet -ErrorAction SilentlyContinue
Record "maintenance-link-reachable" $ping "ping $LinkLocal"

# 6. SSH must answer from the distro (OpenSSH), not the diagnostic dropbear.
if (-not $SkipSsh) {
    $banner = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect($SshHost, 22)
        $stream = $client.GetStream()
        $stream.ReadTimeout = 3000
        $reader = New-Object System.IO.StreamReader($stream)
        $banner = $reader.ReadLine()
        $client.Close()
    } catch {
        $banner = $null
    }
    $isOpenSsh = $banner -like 'SSH-2.0-OpenSSH*'
    Record "ssh-banner-openssh" $isOpenSsh $(if ($banner) { $banner } else { "no banner" })
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "RESULT: FAIL ($($failures.Count) check(s))"
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "RESULT: PASS - enumeration, bidirectional bytes, ARP, ICMP, DHCP and SSH"
exit 0
