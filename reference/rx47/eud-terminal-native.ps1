# EUD terminal: compatible one-byte input, optional native RX41 frames.
param(
    [string]$Port = '',
    [string]$Command,
    [switch]$Native,
    [switch]$Reconnect,
    [ValidateRange(500,10000)][int]$RetryMs = 500,
    [ValidateRange(1,10)][int]$MaxAttempts = 10,
    [ValidateRange(1,60)][int]$TailSeconds = 3,
    [ValidateRange(500,10000)][int]$NativeAckTimeoutMs = 4000,
    [switch]$ShowAcks,
    [string]$LogBase = (Join-Path $env:TEMP ('eud-terminal-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')))
)
$ErrorActionPreference = 'Stop'
$oneShot = $PSBoundParameters.ContainsKey('Command')
if ($oneShot -and $Command -match '[^\x20-\x7e]') { throw 'Command must be one ASCII line.' }
if (!$oneShot -and [Console]::IsInputRedirected) { throw 'Use a real console window, or -Command.' }
if ($Reconnect) {
    if (!(Test-Path 'E:\eud-host\eudtool.exe')) { throw 'Reconnect needs E:\eud-host\eudtool.exe.' }
    $ctlReply = & 'E:\eud-host\eudtool.exe' com-off
    if ($LASTEXITCODE -ne 0) { throw "com-off failed: $ctlReply" }
    $ctlReply = & 'E:\eud-host\eudtool.exe' com-up
    if ($LASTEXITCODE -ne 0) { throw "com-up failed: $ctlReply" }
    Start-Sleep -Milliseconds 800
}
if (!$Port) {
    $devices = @(Get-PnpDevice -PresentOnly -Class Ports -ErrorAction SilentlyContinue |
        Where-Object { $_.FriendlyName -match '9505.*\(COM\d+\)' })
    if ($devices.Count -eq 0 -and (Test-Path 'E:\eud-host\eudtool.exe')) {
        $ctlReply = & 'E:\eud-host\eudtool.exe' com-up
        if ($LASTEXITCODE -ne 0) { throw "com-up failed: $ctlReply" }
        Start-Sleep -Milliseconds 800
        $devices = @(Get-PnpDevice -PresentOnly -Class Ports -ErrorAction SilentlyContinue |
            Where-Object { $_.FriendlyName -match '9505.*\(COM\d+\)' })
    }
    if ($devices.Count -ne 1) { throw 'Cannot select one EUD 9505 port. Specify -Port COM14.' }
    $Port = [regex]::Match($devices[0].FriendlyName, 'COM\d+').Value
}
$sp = [IO.Ports.SerialPort]::new($Port,115200,'None',8,'One')
$sp.ReadTimeout = 100
$sp.WriteTimeout = 500
$sp.DtrEnable = $true
$sp.RtsEnable = $true
$queue = [Collections.Generic.Queue[byte]]::new()
if ($oneShot -or $Native) {
    $queue.Enqueue(0x15) # Ctrl-U clears any earlier incomplete shell line.
}
if ($oneShot) {
    foreach ($b in [Text.Encoding]::ASCII.GetBytes($Command)) { $queue.Enqueue($b) }
    $queue.Enqueue(0x0a)
}
$clock = [Diagnostics.Stopwatch]::StartNew()
$state = @{ AckText=''; Pending=$null; Attempts=0; LastWrite=0L; NextByte=3000L;
    LastActivity=0L; Frames=0; Stray=0; Acked=0; Retries=0; MaxPayload=0; RetryAt=0L;
    DisplayPending=''; DisplayAt=0L; Synchronizing=[bool]$Native; NativeFrames=0 }
$wire = [Collections.Generic.List[byte]]::new()
$utf8 = [Text.UTF8Encoding]::new($false)
$decoder = $utf8.GetDecoder()
$raw = $null
$textLog = $null
$events = $null
$oldCtrlC = $null
$jitter = [Random]::new()

function Show-EudText([string]$chunk) {
    foreach ($character in $chunk.ToCharArray()) {
        if ($state.DisplayPending.Length -gt 0) {
            $state.DisplayPending += $character
            if ($state.DisplayPending[0] -eq [char]27) {
                if ($state.DisplayPending -match '^\x1b\[[0-9;?]*[A-Za-z]$') {
                    # ReadKey cannot relay a terminal-generated cursor reply in time.
                    if ($state.DisplayPending -ne ([string][char]27 + '[6n')) {
                        [Console]::Write($state.DisplayPending)
                    }
                    $state.DisplayPending = ''
                } elseif ($state.DisplayPending.Length -eq 2 -and $character -ne '[') {
                    [Console]::Write($state.DisplayPending)
                    $state.DisplayPending = ''
                }
            } elseif ($character -eq "`n") {
                $receipt = '^\[\s*\d+\.\d+\]\s*eud: (tty byte=[0-9a-f]{2}(?: [a-z0-9_]+=[a-z0-9]+)*|rx frame len=\d+ data=[0-9a-f ]+ s1_after=[0-9a-f]{8}(?: via=(irq|poll))?)\r?\n$'
                if ($ShowAcks -or $state.DisplayPending -notmatch $receipt) {
                    [Console]::Write($state.DisplayPending)
                }
                $state.DisplayPending = ''
            }
        } elseif ($character -eq '[' -or $character -eq [char]27) {
            $state.DisplayPending = [string]$character
            $state.DisplayAt = $clock.ElapsedMilliseconds
        } else { [Console]::Write($character) }
    }
}

function Receive-Eud {
    $available = $sp.BytesToRead
    if ($available -eq 0) { return }
    $buf = [byte[]]::new($available)
    $n = $sp.Read($buf,0,$available)
    if ($n -eq 0) { return }
    $raw.Write($buf,0,$n)
    $raw.Flush()
    $wire.AddRange([byte[]]$buf[0..($n-1)])
    $state.LastActivity = $clock.ElapsedMilliseconds
    while ($wire.Count -ge 2) {
        $length = [int]$wire[1]
        if ($wire[0] -ne 0x90 -or $length -lt 1 -or $length -gt 64) {
            $wire.RemoveAt(0)
            $state.Stray++
            continue
        }
        if ($wire.Count -lt $length + 2) { break }
        $payload = $wire.GetRange(2,$length).ToArray()
        $wire.RemoveRange(0,$length+2)
        $chars = [char[]]::new($length * 2)
        $count = $decoder.GetChars($payload,0,$length,$chars,0,$false)
        $chunk = [string]::new($chars,0,$count)
        Show-EudText $chunk
        $textLog.Write($chunk)
        $state.AckText += $chunk
        if ($state.AckText.Length -gt 4096) { $state.AckText = $state.AckText.Substring($state.AckText.Length-4096) }
        $state.Frames++
        $state.MaxPayload = [Math]::Max($state.MaxPayload,$length)
    }
}

function Send-Pending {
    $payload = [byte[]]@($state.Pending)
    $frame = [byte[]](@(0x90,$payload.Length) + $payload)
    $sp.Write($frame,0,$frame.Length)
    $sp.BaseStream.Flush()
    $state.Attempts++
    $state.LastWrite = $clock.ElapsedMilliseconds
    if ($Native -and !$state.Synchronizing) {
        $state.RetryAt = $state.LastWrite + $NativeAckTimeoutMs
    } else {
        $state.RetryAt = $state.LastWrite + $RetryMs + $jitter.Next(0,400)
    }
    if ($Native) {
        $hex = ($payload | ForEach-Object { $_.ToString('x2') }) -join ' '
        $events.WriteLine(('{0} TX native len={1} data={2} attempt={3} sync={4}' -f
            $state.LastWrite,$payload.Length,$hex,$state.Attempts,$state.Synchronizing))
    } else {
        $events.WriteLine(('{0} TX byte={1:x2} attempt={2}' -f $state.LastWrite,$state.Pending,$state.Attempts))
    }
    if ($state.Attempts -gt 1) { $state.Retries++ }
}

try {
    $logDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($LogBase))
    [void][IO.Directory]::CreateDirectory($logDirectory)
    $raw = [IO.File]::Open($LogBase + '.raw','CreateNew','Write','Read')
    $textLog = [IO.StreamWriter]::new($LogBase + '.txt',$false,$utf8)
    $textLog.AutoFlush = $true
    $events = [IO.StreamWriter]::new($LogBase + '.events.txt',$false,$utf8)
    $events.AutoFlush = $true
    $sp.Open()
    if (!$oneShot) {
        $oldCtrlC = [Console]::TreatControlCAsInput
        [Console]::TreatControlCAsInput = $true
    }
    [Console]::Error.WriteLine("[host] $Port opened; Ctrl-] exits, Ctrl-C interrupts phone, Ctrl-U clears line.")
    if ($Native) {
        [Console]::Error.WriteLine("[host] Native ASCII frames up to 14 bytes; startup Ctrl-U sync, then one attempt per data frame. Logs: $LogBase.*")
    } else {
        [Console]::Error.WriteLine("[host] ASCII input; one byte per frame. Unfiltered logs: $LogBase.*")
    }
    $running = $true
    while ($running) {
        Receive-Eud
        $now = $clock.ElapsedMilliseconds
        if ($state.DisplayPending.Length -gt 0 -and $now - $state.DisplayAt -ge 500) {
            [Console]::Write($state.DisplayPending)
            $state.DisplayPending = ''
        }
        if ($null -ne $state.Pending) {
            $payload = [byte[]]@($state.Pending)
            if ($payload.Length -eq 1) {
                $ack = 'eud: tty byte={0:x2}' -f $payload[0]
            } else {
                $hex = ($payload | ForEach-Object { $_.ToString('x2') }) -join ' '
                $ack = 'eud: rx frame len={0} data={1}' -f $payload.Length,$hex
            }
            if ($state.AckText.Contains($ack)) {
                if ($Native) {
                    $events.WriteLine(('{0} ACK native len={1} data={2}' -f $now,$payload.Length,
                        (($payload | ForEach-Object { $_.ToString('x2') }) -join ' ')))
                    if ($state.Synchronizing) {
                        $state.Synchronizing = $false
                        $events.WriteLine("$now SYNC fresh Ctrl-U receipt; begin native input")
                    } else { $state.NativeFrames++ }
                } else {
                    $events.WriteLine(('{0} ACK byte={1:x2}' -f $now,$state.Pending))
                }
                $state.Acked += $payload.Length
                $state.Pending = $null
                $state.NextByte = $now + 200 + $jitter.Next(0,100)
                $state.LastActivity = $now
            } elseif ($now -ge $state.RetryAt) {
                if ($Native -and !$state.Synchronizing) {
                    throw 'Native frame has no receipt; remaining input stopped. Check captured output before resending because the frame may have executed.'
                }
                if ($state.Attempts -ge $MaxAttempts) {
                    if ($Native) { throw "Startup Ctrl-U has no receipt after $($state.Attempts) attempts; native input was not sent." }
                    throw ('No ACK for byte {0:x2} after {1} attempts; remaining input stopped. The shell line may be partial. Reconnect and Ctrl-U before retrying.' -f $payload[0],$state.Attempts)
                }
                Send-Pending
            }
        }
        if (!$oneShot -and !($Native -and $state.Synchronizing)) {
            while ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                $code = [int]$key.KeyChar
                if ($code -eq 29) { $running = $false; break }
                if ($code -eq 3 -or $code -eq 21) {
                    $queue.Clear()
                    $state.Pending = $null
                    $state.NextByte = $now
                    $events.WriteLine("$now CANCEL queued input for control key")
                }
                switch ($key.Key) {
                    'Enter' { $code = 10 }
                    'Backspace' { $code = 127 }
                }
                if ($code -gt 0 -and $code -lt 128) { $queue.Enqueue([byte]$code) }
                elseif ($code -ge 128) { [Console]::Error.WriteLine('[host] ASCII input only.') }
            }
        }
        if (!$running) { break }
        if ($null -eq $state.Pending -and $queue.Count -gt 0 -and $now -ge $state.NextByte) {
            if ($Native) {
                # Do not combine the harmless startup sync byte with shell input.
                $n = if ($state.Synchronizing) { 1 } else { [Math]::Min(14,$queue.Count) }
                if ($n -eq 2) { $n = 1 } # Length 2 is the header-only F1 command.
                $state.Pending = [byte[]]@(for ($i=0; $i -lt $n; $i++) { $queue.Dequeue() })
            } else {
                $state.Pending = $queue.Dequeue()
            }
            $state.Attempts = 0
            $state.AckText = ''
            Send-Pending
        }
        if ($oneShot -and $queue.Count -eq 0 -and $null -eq $state.Pending -and
            $now - $state.LastActivity -ge $TailSeconds * 1000) { break }
        Start-Sleep -Milliseconds 5
    }
} finally {
    try { if ($sp.IsOpen) { $sp.Close() } } finally {
        $sp.Dispose()
        if ($null -ne $oldCtrlC) { [Console]::TreatControlCAsInput = $oldCtrlC }
        if ($raw) { $raw.Dispose() }
        if ($textLog) { $textLog.Dispose() }
        if ($events) { $events.Dispose() }
        if ($state.DisplayPending) { [Console]::Write($state.DisplayPending) }
        [Console]::Error.WriteLine(('[host] Closed {0}; ACKed={1}, retries={2}, received frames={3}, max payload={4}, stray={5}, buffered bytes={6}' -f
            $Port,$state.Acked,$state.Retries,$state.Frames,$state.MaxPayload,$state.Stray,$wire.Count))
        if ($Native) { [Console]::Error.WriteLine("[host] Native data frames ACKed=$($state.NativeFrames); startup synchronized=$(!$state.Synchronizing)") }
    }
}
