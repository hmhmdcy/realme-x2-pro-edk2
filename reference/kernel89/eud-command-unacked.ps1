param([Parameter(Mandatory)][string]$Command,[Parameter(Mandatory)][string]$Prefix)
# Bounded recovery when printk receipts are disabled. Send each frame once.
$ErrorActionPreference='Stop'
if ($Command -match '[^\x20-\x7e]') {throw 'ASCII command required'}
$path="E:\edk2-samurai-out\kernel89\$Prefix.raw"
if (Test-Path -LiteralPath $path) {throw 'Capture exists'}
$sp=[System.IO.Ports.SerialPort]::new('COM14',115200,'None',8,'One')
$sp.ReadTimeout=100; $sp.WriteTimeout=500; $sp.DtrEnable=$true; $sp.RtsEnable=$true
$raw=$null; $wire=[Collections.Generic.List[byte]]::new(); $decoded=[Text.StringBuilder]::new()
function Drain-Eud {
    if ($sp.BytesToRead -le 0) {return}
    $buf=[byte[]]::new($sp.BytesToRead); $n=$sp.Read($buf,0,$buf.Length)
    $raw.Write($buf,0,$n); $wire.AddRange([byte[]]$buf[0..($n-1)])
    while ($wire.Count -ge 2) {
        $size=[int]$wire[1]
        if ($wire[0] -ne 0x90 -or $size -lt 1 -or $size -gt 64) {$wire.RemoveAt(0);continue}
        if ($wire.Count -lt $size+2) {break}
        [void]$decoded.Append([Text.Encoding]::ASCII.GetString($wire.GetRange(2,$size).ToArray()))
        $wire.RemoveRange(0,$size+2)
    }
}
try {
    $raw=[IO.File]::Open($path,'CreateNew','Write','Read'); $sp.Open()
    $sp.Write([byte[]]@(0x90,1,0x15),0,3)
    $payload=[Text.Encoding]::ASCII.GetBytes($Command+"`n")
    $offset=0; $timer=[Diagnostics.Stopwatch]::StartNew(); $next=1000
    while ($timer.ElapsedMilliseconds -lt 25000) {
        Drain-Eud
        if ($offset -lt $payload.Length -and $timer.ElapsedMilliseconds -ge $next) {
            $size=[Math]::Min(14,$payload.Length-$offset)
            if ($size -eq 2) {$size=1}
            $frame=[byte[]](@(0x90,$size)+$payload[$offset..($offset+$size-1)])
            $sp.Write($frame,0,$frame.Length); $sp.BaseStream.Flush()
            $offset+=$size; $next=$timer.ElapsedMilliseconds+700
        }
        Start-Sleep -Milliseconds 5
    }
    $decoded.ToString() | Set-Content -LiteralPath "E:\edk2-samurai-out\kernel89\$Prefix.txt" -Encoding utf8NoBOM
    Write-Output "Sent $offset/$($payload.Length) command bytes once; decoded $($decoded.Length) bytes"
} finally {
    try {if ($sp.IsOpen) {$sp.Close()}} finally {$sp.Dispose(); if ($raw) {$raw.Dispose()}}
}
