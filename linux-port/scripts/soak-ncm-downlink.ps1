<#
Repeat a fixed-size device-to-host transfer and measure how often it stalls.

The port has an intermittent behaviour: most 32 MiB downlink transfers run at
~250 Mb/s, but occasionally one collapses to ~17 Mb/s.  Hashes always match
(SSH detects and retransmits), so this is a throughput/stall problem, not
corruption.  This script records the distribution so the claim "sometimes
slow" is backed by numbers rather than one run.

Usage:
    soak-ncm-downlink.ps1 -Rounds 20
#>

[CmdletBinding()]
param(
    [int]$Rounds = 20,
    [string]$RemoteFile = "/tmp/up-1.bin",
    [string]$LocalProbe = "E:\edk2-samurai-out\ncm-throughput\probe-32MiB.bin",
    [string]$OutDir = "E:\edk2-samurai-out\ncm-throughput\soak",
    [string]$HostAddress = "172.16.42.1",
    [string]$User = "user",
    [string]$Key = "C:\Users\cy122\.ssh\samurai_id_ed25519",
    [string]$KnownHosts = "C:\Users\cy122\.ssh\samurai_ncm_known_hosts"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$sizeBytes = (Get-Item $LocalProbe).Length
$expected = (Get-FileHash $LocalProbe -Algorithm SHA256).Hash.ToLowerInvariant()
$scp = "C:\Windows\System32\OpenSSH\scp.exe"
$common = @("-F", "NUL", "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=$KnownHosts", "-i", $Key)

Write-Host "probe: $([math]::Round($sizeBytes/1MB,1)) MiB sha256=$expected"
Write-Host ""

$samples = @()
for ($i = 1; $i -le $Rounds; $i++) {
    $dest = Join-Path $OutDir "r$i.bin"
    if (Test-Path $dest) { Remove-Item $dest -Force }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $scp @common "${User}@${HostAddress}:$RemoteFile" $dest 2>&1 | Out-Null
    $sw.Stop()
    $seconds = $sw.Elapsed.TotalSeconds
    $hashOk = (Test-Path $dest) -and
        ((Get-FileHash $dest -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected)
    $mbps = if ($seconds -gt 0) {
        [math]::Round(($sizeBytes * 8 / 1000000) / $seconds, 1)
    } else { 0 }
    $samples += [pscustomobject]@{
        Round = $i; Seconds = [math]::Round($seconds, 2); Mbps = $mbps; HashOk = $hashOk
    }
    Write-Host ("{0,2}: {1,6:N2}s  {2,7} Mb/s  hash={3}" -f
        $i, $seconds, $mbps, $(if ($hashOk) { "OK" } else { "MISMATCH" }))
    Remove-Item $dest -Force -ErrorAction SilentlyContinue
}

$fast = @($samples | Where-Object { $_.Seconds -lt 4 })
$slow = @($samples | Where-Object { $_.Seconds -ge 4 })
$bad = @($samples | Where-Object { -not $_.HashOk })
$median = ($samples | Sort-Object Seconds)[[int]([math]::Floor($samples.Count / 2))].Mbps

Write-Host ""
Write-Host ("rounds={0}  fast(<4s)={1}  slow(>=4s)={2}  mismatched={3}" -f
    $Rounds, $fast.Count, $slow.Count, $bad.Count)
Write-Host ("median throughput={0} Mb/s  min={1}  max={2}" -f
    $median, ($samples | Measure-Object Mbps -Minimum).Minimum,
    ($samples | Measure-Object Mbps -Maximum).Maximum)

$report = Join-Path $OutDir "soak-$((Get-Date).ToString('yyyyMMdd-HHmmss')).json"
$samples | ConvertTo-Json -Depth 3 | Set-Content -Path $report -Encoding UTF8
Write-Host "report: $report"

if ($bad.Count -gt 0) {
    Write-Host "RESULT: FAIL - $($bad.Count) corrupted transfer(s)"
    exit 1
}
if ($slow.Count -gt 0) {
    Write-Host ("RESULT: PASS-WITH-STALLS - no corruption, but {0}/{1} transfers stalled" -f
        $slow.Count, $Rounds)
    exit 2
}
Write-Host "RESULT: PASS - no corruption, no stalls"
exit 0
