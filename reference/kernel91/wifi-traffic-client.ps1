param(
    [Parameter(Mandatory=$true)][string]$PrivateDirectory,
    [Parameter(Mandatory=$true)][string]$LocalAddress
)
$ErrorActionPreference = 'Stop'
$lease = Get-Content -LiteralPath (Join-Path $PrivateDirectory 'dhcp-lease.txt')
$remoteAddress = ($lease | Where-Object { $_ -match '^ip=' }) -replace '^ip=', ''
$size = 4 * 1024 * 1024
$uploadPath = Join-Path $PrivateDirectory 'traffic-upload-source.bin'
$downloadPath = Join-Path $PrivateDirectory 'traffic-download.bin'
if (Test-Path -LiteralPath $uploadPath) { throw 'Refusing to overwrite upload source' }
if (Test-Path -LiteralPath $downloadPath) { throw 'Refusing to overwrite download' }
$bytes = New-Object byte[] $size
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
[System.IO.File]::WriteAllBytes($uploadPath, $bytes)
foreach ($direction in @('D', 'U')) {
    $endpoint = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse($LocalAddress), 0)
    $client = [System.Net.Sockets.TcpClient]::new($endpoint)
    try {
        $client.ReceiveTimeout = 20000
        $client.SendTimeout = 20000
        $client.Connect($remoteAddress, 18091)
        $stream = $client.GetStream()
        $stream.WriteByte([byte][char]$direction)
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        if ($direction -eq 'D') {
            $file = [System.IO.File]::Open($downloadPath, 'CreateNew', 'Write', 'None')
            try {
                $buffer = New-Object byte[] 16384
                $total = 0
                while ($total -lt $size) {
                    $count = $stream.Read($buffer, 0, [Math]::Min($buffer.Length, $size - $total))
                    if ($count -le 0) { throw 'Short Wi-Fi download' }
                    $file.Write($buffer, 0, $count)
                    $total += $count
                }
            } finally { $file.Dispose() }
        } else {
            $stream.Write($bytes, 0, $bytes.Length)
            if ($stream.ReadByte() -ne 79 -or $stream.ReadByte() -ne 75) { throw 'Upload acknowledgement failed' }
        }
        $timer.Stop()
        [pscustomobject]@{ Direction=$direction; Bytes=$size; Seconds=$timer.Elapsed.TotalSeconds }
    } finally { $client.Dispose() }
}
Get-FileHash -Algorithm SHA256 -LiteralPath $uploadPath,$downloadPath | Select-Object Hash
