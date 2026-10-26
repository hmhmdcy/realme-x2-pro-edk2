# One-shot bootstrap/file verification over the direct USB link.
param(
    [ValidateSet('Receive','Send')][string]$Mode,
    [string]$Address = '169.254.42.1',
    [int]$Port = 2223,
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][long]$ExpectedBytes
)
$ErrorActionPreference = 'Stop'
$client = [Net.Sockets.TcpClient]::new()
$file = $null
$stream = $null
try {
    $pending = $client.ConnectAsync($Address,$Port)
    if (!$pending.Wait(5000)) { throw 'USB TCP connect timeout' }
    $client.ReceiveTimeout = 30000
    $client.SendTimeout = 30000
    $stream = $client.GetStream()
    if ($Mode -eq 'Receive') {
        $file = [IO.File]::Open($Path,'CreateNew','Write','None')
        $stream.CopyTo($file)
        $file.Flush()
        if ($file.Length -ne $ExpectedBytes) { throw "Length mismatch: $($file.Length)" }
    } else {
        $file = [IO.File]::OpenRead($Path)
        if ($file.Length -ne $ExpectedBytes) { throw "Length mismatch: $($file.Length)" }
        $file.CopyTo($stream)
        $stream.Flush()
        $client.Client.Shutdown([Net.Sockets.SocketShutdown]::Send)
    }
} finally {
    if ($file) { $file.Dispose() }
    if ($stream) { $stream.Dispose() }
    $client.Dispose()
}
[pscustomobject]@{mode=$Mode;address=$Address;port=$Port;bytes=$ExpectedBytes;sha256=(Get-FileHash -LiteralPath $Path).Hash.ToLowerInvariant()}
