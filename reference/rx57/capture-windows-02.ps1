$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx57'
$rxControl=Join-Path $rxRoot 'control-02'
$rxStatus=Get-Content -Raw -LiteralPath (Join-Path $rxControl 'status.json') | ConvertFrom-Json
if($rxStatus.phase -ne 'ready' -or !$rxStatus.registry_enabled -or !$rxStatus.driver_reloaded){throw 'Approved logger helper is not ready.'}
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
if(Test-Path -LiteralPath (Join-Path $rxRoot 'windows-log-02.raw')){throw 'Original capture already exists.'}
try {
    & (Join-Path $rxRoot 'eud-terminal-rx-perf.ps1') -Port COM14 -Native -RxAudit -AuditMaxSeconds 180 -MaxAttempts 2 -LogBase (Join-Path $rxRoot 'windows-log-02')
} finally {
    # The diagnostic owns/settles/closes its serial handle in its own finally.
    [IO.File]::WriteAllText((Join-Path $rxControl 'restore.request'),'restore after diagnostic finally'+"`n",[Text.UTF8Encoding]::new($false))
}
