param([string]$Port = 'COM14', [int]$Seconds = 100, [Parameter(Mandatory=$true)][string]$Out,
      [switch]$StartAbc, [ValidateSet('RX38-UEFI','RX39-UEFI','RX41-WAIT')][string]$Marker = 'RX39-UEFI')
$ErrorActionPreference = 'Stop'
if ($Seconds -lt 1 -or $Seconds -gt 150) { throw 'Seconds must be 1..150' }
$sp = [System.IO.Ports.SerialPort]::new($Port,115200,'None',8,'One')
$sp.ReadTimeout = 100; $sp.WriteTimeout = 500
$sp.DtrEnable = $true; $sp.RtsEnable = $true
$raw = $null; $txt = $null; $events = $null
$timer = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $raw = [System.IO.File]::Open($Out + '.raw', 'CreateNew', 'Write', 'Read')
    $txt = [System.IO.StreamWriter]::new($Out + '.txt', $false)
    $events = [System.IO.StreamWriter]::new($Out + '.events.txt', $false)
    $sp.Open()
    Write-Output "Opened $Port; bounded UEFI capture"
    $pending = [System.Collections.Generic.List[byte]]::new()
    $text = [System.Text.StringBuilder]::new()
    $patterns = @([byte[]]@(0x90,3,0x41,0x42,0x43), [byte[]]@(0x90,4,0x44,0x45,0x46,0x47))
    $names = @('ABC','DEFG')
    $sent = @(0,0); $last = @(-4000L,-4000L)
    $frames = 0; $stray = 0
    while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        $available = $sp.BytesToRead
        if ($available -gt 0) {
            $buf = [byte[]]::new($available)
            $n = $sp.Read($buf,0,$available)
            if ($n -gt 0) {
                $raw.Write($buf,0,$n); $raw.Flush()
                $pending.AddRange([byte[]]$buf[0..($n-1)])
            }
            while ($pending.Count -ge 2) {
                $length = [int]$pending[1]
                if ($pending[0] -ne 0x90 -or $length -lt 1 -or $length -gt 64) {
                    $pending.RemoveAt(0); $stray++; continue
                }
                if ($pending.Count -lt $length + 2) { break }
                $part = [System.Text.Encoding]::ASCII.GetString($pending.GetRange(2,$length).ToArray())
                [void]$text.Append($part); $txt.Write($part); $txt.Flush()
                $pending.RemoveRange(0,$length+2); $frames++
            }
        }
        for ($i = 0; $i -lt 2; $i++) {
            # The first ready marker may precede Windows opening the port.
            # ABC can start immediately; DEFG requires an observed UEFI marker.
            $ready = ($StartAbc.IsPresent -and $i -eq 0) -or $text.ToString().Contains($Marker + ' READY ' + $names[$i])
            if ($ready -and
                -not $text.ToString().Contains($Marker + ' RESULT ' + $names[$i]) -and
                -not $text.ToString().Contains($Marker + ' TIMEOUT ' + $names[$i]) -and
                $sent[$i] -lt 3 -and $timer.ElapsedMilliseconds -ge $last[$i] + 3000) {
                $frame = $patterns[$i]
                $sp.Write($frame,0,$frame.Length)
                $sp.BaseStream.Flush()
                $sent[$i]++; $last[$i] = $timer.ElapsedMilliseconds
                $line = "$($last[$i])ms OUT $($names[$i]) attempt=$($sent[$i]) hex=$([BitConverter]::ToString($frame))"
                $events.WriteLine($line); $events.Flush(); Write-Output $line
            }
        }
        Start-Sleep -Milliseconds 5
    }
    $summary = "finished frames=$frames stray=$stray pending=$($pending.Count) sent=$($sent -join ',')"
    $events.WriteLine($summary); Write-Output $summary
} finally {
    try { if ($sp.IsOpen) { $sp.Close() } } finally {
        $sp.Dispose()
        foreach ($stream in @($raw,$txt,$events)) { if ($null -ne $stream) { $stream.Dispose() } }
    }
    Write-Output "Closed/disposed $Port"
}
