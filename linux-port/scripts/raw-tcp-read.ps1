<#
Read one TCP stream from the device and report length/throughput.

Used instead of scp/ssh when diagnosing whether a short transfer is caused
below SSH.  Start `nc -l -p 9000 < /tmp/up-1.bin` on the device first.
#>

param(
    [string]$HostAddress = "172.16.42.1",
    [int]$Port = 9000,
    [int64]$ExpectedBytes = 33554432,
    [string]$OutFile
)

$client = New-Object System.Net.Sockets.TcpClient
$client.NoDelay = $true
$client.ReceiveBufferSize = 4 * 1024 * 1024
$client.Connect($HostAddress, $Port)
$stream = $client.GetStream()
$buffer = New-Object byte[] 262144
[int64]$total = 0
$fs = if ($OutFile) { [System.IO.File]::Create($OutFile) } else { $null }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($true) {
    $read = $stream.Read($buffer, 0, $buffer.Length)
    if ($read -le 0) { break }
    $total += $read
    if ($fs) { $fs.Write($buffer, 0, $read) }
}
$sw.Stop()
if ($fs) { $fs.Dispose() }
$client.Close()
$mbps = if ($sw.Elapsed.TotalSeconds -gt 0) {
    [math]::Round(($total * 8 / 1000000) / $sw.Elapsed.TotalSeconds, 1)
} else { 0 }
Write-Output ("bytes={0}/{1} seconds={2:N2} mbps={3} complete={4}" -f
    $total, $ExpectedBytes, $sw.Elapsed.TotalSeconds, $mbps, ($total -eq $ExpectedBytes))
