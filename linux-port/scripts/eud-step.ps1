param([Parameter(Mandatory=$true)][string]$Port, [string]$Hex = '',
      [ValidateRange(1,5)][int]$Repeat = 1,
      [ValidateRange(1,60)][int]$Seconds = 20,
      [Parameter(Mandatory=$true)][string]$Out, [string]$Ack = '',
      [ValidateRange(2,30)][int]$TailSeconds = 2,
      [ValidateRange(0,1000)][int]$RetryJitterMs = 0)
$ErrorActionPreference = 'Stop'
$textPath = [IO.Path]::ChangeExtension($Out, '.txt')
$eventsPath = [IO.Path]::ChangeExtension($Out, '.events.txt')
if ($textPath -eq $Out -or $eventsPath -eq $Out) { throw 'Use a .raw capture path.' }
foreach ($path in @($Out,$textPath,$eventsPath)) {
    if (Test-Path -LiteralPath $path) { throw "Capture path exists: $path" }
}
$frame = [byte[]]@($Hex.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries) |
    ForEach-Object { [Convert]::ToByte($_,16) })
if ($frame.Length -gt 0 -and !(
    $frame.Length -ge 2 -and $frame[0] -eq 0x90 -and (
        ($frame[1] -eq 2 -and $frame.Length -eq 2) -or
        (($frame[1] -eq 1 -or ($frame[1] -ge 3 -and $frame[1] -le 14)) -and
         $frame.Length -eq $frame[1] + 2)))) {
    throw 'Use one complete 0x90 frame: len=1 or 3..14 tty; header-only len=2 F1.'
}
$sp = [System.IO.Ports.SerialPort]::new($Port,115200,'None',8,'One')
$sp.ReadTimeout = 100
$sp.WriteTimeout = 500
$sp.DtrEnable = $true
$sp.RtsEnable = $true
$raw = $null
$txt = $null
$events = $null
try {
    $raw = [System.IO.File]::Open($Out, 'CreateNew', 'Write', 'Read')
    $txt = [System.IO.StreamWriter]::new($textPath, $false)
    $txt.AutoFlush = $true
    $events = [System.IO.StreamWriter]::new($eventsPath, $false)
    $events.AutoFlush = $true
    $sp.Open()
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $sent = 0
    $nextSendMs = 3000
    $ackedAt = $null
    $pending = [System.Collections.Generic.List[byte]]::new()
    $decoded = [System.Text.StringBuilder]::new()
    $frames = 0
    $stray = 0
    while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        $available = $sp.BytesToRead
        if ($available -gt 0) {
            $buf = [byte[]]::new($available)
            $n = $sp.Read($buf,0,$available)
            $raw.Write($buf,0,$n)
            $raw.Flush()
            $pending.AddRange([byte[]]$buf[0..($n-1)])
            while ($pending.Count -ge 2) {
                $length = [int]$pending[1]
                if ($pending[0] -ne 0x90 -or $length -eq 0 -or $length -gt 64) {
                    $pending.RemoveAt(0)
                    $stray++
                    continue
                }
                if ($pending.Count -lt $length + 2) { break }
                $part = [System.Text.Encoding]::ASCII.GetString(
                    $pending.GetRange(2,$length).ToArray())
                [void]$decoded.Append($part)
                $txt.Write($part)
                $pending.RemoveRange(0,$length+2)
                $frames++
            }
            if ($Ack -and $sent -gt 0 -and $null -eq $ackedAt -and
                $decoded.ToString().Contains($Ack)) {
                Write-Output "ACK: $Ack; stop retries"
                $ackedAt = $timer.ElapsedMilliseconds
                $events.WriteLine("$ackedAt ACK: $Ack")
            }
        }
        if ($null -ne $ackedAt -and $timer.ElapsedMilliseconds -ge $ackedAt + $TailSeconds * 1000) { break }
        if ($frame.Length -gt 0 -and $sent -lt $Repeat -and
            $null -eq $ackedAt -and
            $timer.ElapsedMilliseconds -ge $nextSendMs) {
            if ($sent -eq 0) { [void]$decoded.Clear() }
            $sp.Write($frame,0,$frame.Length)
            $sp.BaseStream.Flush()
            $sent++
            if ($RetryJitterMs -gt 0) {
                $nextSendMs = $timer.ElapsedMilliseconds + 3000 +
                    (Get-Random -Minimum 0 -Maximum ($RetryJitterMs + 1))
            } else {
                $nextSendMs = 3000 + 3000 * $sent
            }
            $line = "TX $sent at $($timer.ElapsedMilliseconds)ms: $Hex"
            $events.WriteLine($line)
            Write-Output $line
        }
        Start-Sleep -Milliseconds 5
    }
    $summary = "sent=$sent receipt=$($null -ne $ackedAt) frames=$frames stray=$stray pending=$($pending.Count)"
    $events.WriteLine($summary)
    Write-Output $summary
    Write-Output "Full decoded capture: $textPath"
} finally {
    try { if ($sp.IsOpen) { $sp.Close() } } finally {
        $sp.Dispose()
        foreach ($stream in @($raw,$txt,$events)) {
            if ($null -ne $stream) { $stream.Dispose() }
        }
    }
    Write-Output "Closed $Port; capture $Out"
}
