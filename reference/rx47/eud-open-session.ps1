param([string]$Port='COM14',[string]$Out='E:\edk2-samurai-out\rx47\open-once')
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new($Port,115200,'None',8,'One')
$sp.ReadTimeout=100
$sp.WriteTimeout=500
$sp.DtrEnable=$true
$sp.RtsEnable=$true
$step=0
function Invoke-OneFrame([byte[]]$Frame,[string]$Ack,[string]$Label) {
    $prefix=$Out+'.'+('{0:d2}' -f $script:step)+'-'+$Label
    foreach($suffix in @('.raw','.txt','.events.txt')) {
        if(Test-Path -LiteralPath ($prefix+$suffix)) { throw 'Capture exists' }
    }
    $raw=$null; $txt=$null; $events=$null
    try {
        $raw=[IO.File]::Open($prefix+'.raw','CreateNew','Write','Read')
        $txt=[IO.StreamWriter]::new($prefix+'.txt',$false); $txt.AutoFlush=$true
        $events=[IO.StreamWriter]::new($prefix+'.events.txt',$false); $events.AutoFlush=$true
        $timer=[Diagnostics.Stopwatch]::StartNew()
        $pending=[Collections.Generic.List[byte]]::new()
        $decoded=[Text.StringBuilder]::new()
        $sent=$false; $acked=$null; $frames=0; $stray=0
        while($timer.Elapsed.TotalSeconds -lt 10) {
            $available=$sp.BytesToRead
            if($available -gt 0) {
                $buf=[byte[]]::new($available)
                $n=$sp.Read($buf,0,$available)
                $raw.Write($buf,0,$n); $raw.Flush()
                $pending.AddRange([byte[]]$buf[0..($n-1)])
                while($pending.Count -ge 2) {
                    $len=[int]$pending[1]
                    if($pending[0] -ne 0x90 -or $len -eq 0 -or $len -gt 64) {
                        $pending.RemoveAt(0); $stray++; continue
                    }
                    if($pending.Count -lt $len+2) { break }
                    $part=[Text.Encoding]::ASCII.GetString($pending.GetRange(2,$len).ToArray())
                    [void]$decoded.Append($part); $txt.Write($part)
                    $pending.RemoveRange(0,$len+2); $frames++
                }
                if($sent -and $null -eq $acked -and $decoded.ToString().Contains($Ack)) {
                    $acked=$timer.ElapsedMilliseconds
                    $events.WriteLine("$acked ACK: $Ack")
                }
            }
            if($null -ne $acked -and $timer.ElapsedMilliseconds -ge $acked+2000) { break }
            if(!$sent -and $timer.ElapsedMilliseconds -ge 3000) {
                [void]$decoded.Clear()
                $sp.Write($Frame,0,$Frame.Length); $sp.BaseStream.Flush(); $sent=$true
                $hex=($Frame | ForEach-Object {$_.ToString('x2')}) -join ' '
                $events.WriteLine("TX 1 at $($timer.ElapsedMilliseconds)ms: $hex")
            }
            Start-Sleep -Milliseconds 10
        }
        $ok=$null -ne $acked
        $events.WriteLine("sent=1 receipt=$ok frames=$frames stray=$stray pending=$($pending.Count)")
        Write-Output "STEP $script:step $Label receipt=$ok frames=$frames stray=$stray pending=$($pending.Count)"
        Write-Output ($decoded.ToString().Replace([string][char]27,'<ESC>'))
        Write-Output "Capture: $prefix"
    } finally {
        if($events) {$events.Dispose()}
        if($txt) {$txt.Dispose()}
        if($raw) {$raw.Dispose()}
    }
}
try {
    $sp.Open()
    Write-Output "OPENED $Port once; manual commands: u=one Ctrl-U, a/b/c=one native echo, i=id, x=close. No automatic retries."
    while($step -lt 12) {
        Write-Output 'COMMAND>'
        $choice=[Console]::ReadLine()
        if($null -eq $choice -or $choice -eq 'x') {break}
        $payload=$null
        switch($choice) {
            'u' {$payload=[byte[]]@(0x15); $label='ctrl-u'; $ack='tty byte=15'}
            'a' {$payload=[Text.Encoding]::ASCII.GetBytes("echo R47A1234`n"); $label='native-a'; $ack='data=65 63 68 6f 20 52 34 37 41 31 32 33 34 0a'}
            'b' {$payload=[Text.Encoding]::ASCII.GetBytes("echo R47B1234`n"); $label='native-b'; $ack='data=65 63 68 6f 20 52 34 37 42 31 32 33 34 0a'}
            'c' {$payload=[Text.Encoding]::ASCII.GetBytes("echo R47C`n"); $label='native-c'; $ack='data=65 63 68 6f 20 52 34 37 43 0a'}
            'i' {$payload=[Text.Encoding]::ASCII.GetBytes("id`n"); $label='native-id'; $ack='data=69 64 0a'}
            default {Write-Output 'Unknown manual command'; continue}
        }
        if($null -eq $payload) {continue}
        if($payload.Length -ne 1 -and ($payload.Length -lt 3 -or $payload.Length -gt 14)) {throw 'Invalid tty length'}
        $step++
        $frame=[byte[]](@(0x90,$payload.Length)+$payload)
        Invoke-OneFrame $frame $ack $label
    }
} finally {
    $sp.Close(); $sp.Dispose()
    Write-Output "Closed/disposed $Port; manual steps=$step"
}
