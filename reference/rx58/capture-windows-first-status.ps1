$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx58'
$rxControl=Join-Path $rxRoot 'control-first-status-01'
$rxStatus=Get-Content -Raw -LiteralPath (Join-Path $rxControl 'status.json') | ConvertFrom-Json
if($rxStatus.phase -ne 'ready' -or !$rxStatus.registry_enabled -or !$rxStatus.driver_reloaded -or !$rxStatus.etw_started){throw 'Separately approved ETW/logger helper is not ready.'}
$rxProcess=[Diagnostics.Process]::GetProcessById([int]$rxStatus.pid)
if($rxProcess.HasExited){throw 'Logger helper already exited.'}
$rxAge=([DateTime]::UtcNow-[DateTime]::Parse($rxStatus.utc).ToUniversalTime()).TotalSeconds
if($rxAge -lt 0 -or $rxAge -gt 60){throw 'Capture did not start within the prepared deadline.'}
foreach($rxItem in @(
    @('EudRxAudit.cs','006731216176277609d2cff890fe06d8ee9ea99488bea3584036b9b84c673dd7'),
    @('EudSerialPerf.cs','249b3d470ee8172fd2bb07376aa15707b82cb732ad78ddd1ef300ddc7e4ae5d6'),
    @('eud-terminal-rx-perf.ps1','418979e3c6d4321cc39d23eba8d7cc73b31aa8be5e0a5a3d47c76937fa3d1817'))){
    if((Get-FileHash -LiteralPath (Join-Path $rxRoot $rxItem[0])).Hash.ToLower() -ne $rxItem[1]){throw 'Frozen RX55 diagnostic differs.'}
}
if(@(Get-ChildItem -LiteralPath $rxRoot -Filter 'first-status-owner-*.raw').Count){throw 'This capture cannot be repeated.'}
$rxCaptureTimer=[Diagnostics.Stopwatch]::StartNew()
try {
    foreach($rxOwner in 1..3){
        if($rxCaptureTimer.ElapsedMilliseconds -gt 70000){throw 'Final owner would exceed the global capture bound.'}
        $rxSeconds=if($rxOwner -lt 3){20}else{90}
        Write-Output "RX58 owner $rxOwner/3: manual Ctrl-P after sync; first two owners close with Ctrl-]. Final owner exports one frozen journal."
        & (Join-Path $rxRoot 'eud-terminal-rx-perf.ps1') -Port COM14 -Native -RxAudit -AuditMaxSeconds $rxSeconds -MaxAttempts 2 -LogBase (Join-Path $rxRoot ("first-status-owner-$rxOwner"))
        $rxClosed=Get-Content -LiteralPath (Join-Path $rxRoot ("first-status-owner-$rxOwner.rx-audit.jsonl")) | Select-Object -Last 1 | ConvertFrom-Json
        if($rxClosed.event -ne 'closed' -or $rxClosed.serial_is_open -or $rxClosed.pending_input){throw 'Owner did not close cleanly with no pending input.'}
        $rxEvents=Get-Content -Raw -LiteralPath (Join-Path $rxRoot ("first-status-owner-$rxOwner.events.txt"))
        if($rxEvents -notmatch '(?m)^\d+ SYNC fresh Ctrl-U receipt'){throw 'No fresh startup receipt; stop this experiment.'}
        if($rxOwner -lt 3 -and $rxEvents -match '(?m)^\d+ TX native .*sync=False'){throw 'Unexpected data input in startup-only owner.'}
    }
} finally {
    # The unchanged diagnostic closes/disposes its handle before returning here.
    [IO.File]::WriteAllText((Join-Path $rxControl 'restore.request'),'restore after all serial finally blocks'+"`n",[Text.UTF8Encoding]::new($false))
}
