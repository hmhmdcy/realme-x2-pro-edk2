$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx60'
$rxControl=Join-Path $rxRoot 'control-even-01'
$rxStatus=Get-Content -Raw -LiteralPath (Join-Path $rxControl 'status.json') | ConvertFrom-Json
if($rxStatus.phase -ne 'ready' -or !$rxStatus.registry_enabled -or !$rxStatus.driver_reloaded -or !$rxStatus.etw_started){throw 'Authorized ETW/logger helper is not ready.'}
$rxProcess=[Diagnostics.Process]::GetProcessById([int]$rxStatus.pid)
if($rxProcess.HasExited){throw 'Logger helper exited.'}
$rxAge=([DateTime]::UtcNow-[DateTime]::Parse($rxStatus.utc).ToUniversalTime()).TotalSeconds
if($rxAge -lt 0 -or $rxAge -gt 60){throw 'Capture did not start within deadline.'}
foreach($rxItem in @(
    @('EudRxAudit.cs','006731216176277609d2cff890fe06d8ee9ea99488bea3584036b9b84c673dd7'),
    @('EudSerialPerf.cs','249b3d470ee8172fd2bb07376aa15707b82cb732ad78ddd1ef300ddc7e4ae5d6'),
    @('eud-terminal-rx-perf.ps1','418979e3c6d4321cc39d23eba8d7cc73b31aa8be5e0a5a3d47c76937fa3d1817'))){
    if((Get-FileHash -LiteralPath (Join-Path $rxRoot $rxItem[0])).Hash.ToLower() -ne $rxItem[1]){throw 'Frozen diagnostic differs.'}
}
if(@(Get-ChildItem -LiteralPath $rxRoot -Filter 'even-owner-*.raw').Count){throw 'Single-use experiment already attempted.'}
$rxCaptureTimer=[Diagnostics.Stopwatch]::StartNew()
try {
    foreach($rxOwner in 1..2){
        if($rxCaptureTimer.ElapsedMilliseconds -gt 60000){throw 'Final owner would exceed global 180-second bound.'}
        $rxSeconds=if($rxOwner -eq 1){60}else{100}
        Write-Output "RX60 owner $rxOwner/2: first owner sends one unexecuted abc/abcd frame after fresh sync, drains and closes manually. Second freezes/exports one journal then closes."
        & (Join-Path $rxRoot 'eud-terminal-rx-perf.ps1') -Port COM14 -Native -RxAudit -AuditMaxSeconds $rxSeconds -MaxAttempts 2 -LogBase (Join-Path $rxRoot ("even-owner-$rxOwner"))
        $rxClosed=Get-Content -LiteralPath (Join-Path $rxRoot ("even-owner-$rxOwner.rx-audit.jsonl")) | Select-Object -Last 1 | ConvertFrom-Json
        if($rxClosed.event -ne 'closed' -or $rxClosed.serial_is_open -or $rxClosed.pending_input -or $rxClosed.queued_input -or $rxClosed.buffered_bytes -or $rxClosed.stray){throw 'Owner did not drain/close cleanly.'}
        $rxEvents=Get-Content -Raw -LiteralPath (Join-Path $rxRoot ("even-owner-$rxOwner.events.txt"))
        if($rxEvents -notmatch '(?m)^\d+ SYNC fresh Ctrl-U receipt'){throw 'No fresh startup receipt.'}
        if($rxOwner -eq 1){
            if($rxClosed.received_frames % 2 -ne 0){throw 'First owner did not finish with observed even IN frame count.'}
            if(@([regex]::Matches($rxEvents,'(?m)^\d+ TX native .*sync=True')).Count -ne 1){throw 'First owner startup retry changed OUT parity.'}
            if(@([regex]::Matches($rxEvents,'(?m)^\d+ TX native .*sync=False')).Count -ne 1 -or $rxEvents -notmatch '(?m)^\d+ TX native len=(?:3|4) data=61 62 63(?: 64)? attempt=1 sync=False\r?$'){throw 'First owner was not the specified single unexecuted frame.'}
            if($rxClosed.ms -ge 60000){throw 'First owner was not manually closed before deadline.'}
        }
    }
} finally {
    [IO.File]::WriteAllText((Join-Path $rxControl 'restore.request'),'restore after serial finally blocks'+"`n",[Text.UTF8Encoding]::new($false))
}
