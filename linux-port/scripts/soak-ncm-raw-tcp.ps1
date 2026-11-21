<#
Measure device-to-host transfer with a plain TCP stream, bypassing SSH.

SSH has its own windowing and retransmission, which confuses the picture:
a truncated download could be an SSH-level abort or a USB-level loss.  This
script has the device serve a file with `nc` and reads it with a raw
TcpClient, so any short read is a loss below SSH.

Start the server on the device first:

    nc -l -p 9000 < /tmp/up-1.bin

then run:

    soak-ncm-raw-tcp.ps1 -Rounds 10
#>

[CmdletBinding()]
param(
    [int]$Rounds = 10,
    [string]$HostAddress = "172.16.42.1",
    [int]$Port = 9000,
    [int64]$ExpectedBytes = 33554432
)

$ErrorActionPreference = "Stop"
$samples = @()

for ($i = 1; $i -le $Rounds; $i++) {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.NoDelay = $true
    $client.ReceiveBufferSize = 4 * 1024 * 1024
    try {
        $client.Connect($HostAddress, $Port)
    } catch {
        Write-Host "$i: connect failed: $($_.Exception.Message)"
        break
    }
    $stream = $client.GetStream()
    $buffer = New-Object byte[] 262144
    [int64]$total = 0
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($true) {
        $read = $stream.Read($buffer, 0, $buffer.Length)
        if ($read -le 0) { break }
        $total += $read
    }
    $sw.Stop()
    $client.Close()
    $mbps = if ($sw.Elapsed.TotalSeconds -gt 0) {
        [math]::Round(($total * 8 / 1000000) / $sw.Elapsed.TotalSeconds, 1)
    } else { 0 }
    $ok = $total -eq $ExpectedBytes
    $samples += [pscustomobject]@{
        Round = $i; Bytes = $total; Seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        Mbps = $mbps; Complete = $ok
    }
    Write-Host ("{0,2}: {1,6:N2}s  {2,7} Mb/s  bytes={3}/{4} {5}" -f
        $i, $sw.Elapsed.TotalSeconds, $mbps, $total, $ExpectedBytes,
        $(if ($ok) { "OK" } else { "SHORT" }))
}

$short = @($samples | Where-Object { -not $_.Complete })
Write-Host ""
Write-Host ("rounds={0} complete={1} short={2}" -f
    $samples.Count, ($samples.Count - $short.Count), $short.Count)
if ($samples.Count -gt 0) {
    Write-Host ("median={0} Mb/s min={1} max={2}" -f
        (($samples | Sort-Object Seconds)[[int]($samples.Count/2)].Mbps),
        ($samples | Measure-Object Mbps -Minimum).Minimum,
        ($samples | Measure-Object Mbps -Maximum).Maximum)
}
if ($short.Count -gt 0) {
    Write-Host "RESULT: FAIL - short reads below SSH (USB/link loss)"
    exit 1
}
Write-Host "RESULT: PASS - raw TCP stream delivered every byte"
exit 0
