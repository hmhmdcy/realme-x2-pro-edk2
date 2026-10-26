param([string]$Port='COM14',[int]$Seconds=50,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$sp=[IO.Ports.SerialPort]::new($Port,115200,'None',8,'One')
$sp.ReadTimeout=100; $sp.WriteTimeout=500; $sp.DtrEnable=$true; $sp.RtsEnable=$true
$raw=$null; $txt=$null; $events=$null
$pending=[Collections.Generic.List[byte]]::new()
$frames=0; $stray=0
try {
    $raw=[IO.File]::Open($Out+'.raw','CreateNew','Write','Read')
    $txt=[IO.StreamWriter]::new($Out+'.txt',$false)
    $events=[IO.StreamWriter]::new($Out+'.events.txt',$false)
    $sp.Open()
    $timer=[Diagnostics.Stopwatch]::StartNew()
    Write-Output "Passive capture opened $Port; no OUT"
    while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        $available=$sp.BytesToRead
        if ($available -gt 0) {
            $buf=[byte[]]::new($available)
            $n=$sp.Read($buf,0,$available)
            if ($n -gt 0) {
                $raw.Write($buf,0,$n); $raw.Flush()
                $pending.AddRange([byte[]]$buf[0..($n-1)])
            }
            while ($pending.Count -ge 2) {
                $length=[int]$pending[1]
                if ($pending[0] -ne 0x90 -or $length -lt 1 -or $length -gt 64) { $pending.RemoveAt(0); $stray++; continue }
                if ($pending.Count -lt $length+2) { break }
                $part=[Text.Encoding]::ASCII.GetString($pending.GetRange(2,$length).ToArray())
                $txt.Write($part); $txt.Flush(); $pending.RemoveRange(0,$length+2); $frames++
            }
        }
        Start-Sleep -Milliseconds 5
    }
    $line="sent=0 frames=$frames stray=$stray pending=$($pending.Count)"
    $events.WriteLine($line); Write-Output $line
} finally {
    try { if ($sp.IsOpen) { $sp.Close() } } finally {
        $sp.Dispose()
        foreach ($stream in @($raw,$txt,$events)) { if ($null -ne $stream) { $stream.Dispose() } }
    }
    Write-Output "Closed/disposed $Port"
}
