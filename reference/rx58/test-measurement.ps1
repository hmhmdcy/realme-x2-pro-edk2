$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx58'
$rxAdminPath=Join-Path $rxRoot 'driver-log-etw-admin.ps1'
$rxAdminHash=(Get-FileHash -LiteralPath $rxAdminPath).Hash
$rxSource=Get-Content -Raw -LiteralPath $rxAdminPath
$rxTokens=$null;$rxParseErrors=$null
$rxAst=[Management.Automation.Language.Parser]::ParseInput($rxSource,[ref]$rxTokens,[ref]$rxParseErrors)
if($rxParseErrors.Count){throw ($rxParseErrors | Out-String)}
$rxCaptureTokens=$null;$rxCaptureErrors=$null
$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $rxRoot 'capture-windows-first-status.ps1'),[ref]$rxCaptureTokens,[ref]$rxCaptureErrors)
if($rxCaptureErrors.Count){throw ($rxCaptureErrors | Out-String)}
# Reuse the already reviewed in-memory registry fake. No real registry/PnP/ETW IO.
$rxOldTest=Get-Content -Raw -LiteralPath 'E:\edk2-samurai-out\rx57\test-prepared-02.ps1'
$rxFakeClass=[regex]::Match($rxOldTest,"(?s)Add-Type -TypeDefinition @'.*?'@").Value
if(!$rxFakeClass){throw 'Old fake registry class not found.'}
Invoke-Expression $rxFakeClass
$rxResults=@()
$rxTestId=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff')
foreach($rxCase in @('success','second-write','first-reload','trace-start','trace-update','trace-stop','external-conflict')){
    $rxFixture=Join-Path $rxRoot ('mock-'+$rxTestId+'-'+$rxCase)
    [IO.Directory]::CreateDirectory($rxFixture) | Out-Null
    $rxFake=[Rx57FakeRegistry]::new($rxCase)
    $rxTraceCalls=@{start=0;stop=0}
    $rxSim=$rxSource.Replace("param([ValidateSet('Plan','Arm')][string]`$Mode='Plan')","`$Mode='Arm'")
    # Real helper is a script file: its script-scoped trace flags share the
    # declarations/status reads. A invoked mock scriptblock needs that scope
    # stated explicitly, otherwise its local flags shadow the simulated ones.
    $rxSim=$rxSim.Replace('$rxTraceStarted','$script:rxTraceStarted').Replace('$rxTraceStopped','$script:rxTraceStopped')
    $rxSim=$rxSim.Replace("`$rxRoot='E:\edk2-samurai-out\rx58'","`$rxRoot='$rxFixture'")
    $rxSim=$rxSim.Replace('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$false)','$rxFake.OpenReadKey()')
    $rxSim=$rxSim.Replace('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$true)','$rxFake.OpenWriteKey()')
    foreach($rxFunction in $rxAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){
        if($rxFunction.Name -in @('Assert-RxIdentity','Assert-RxNoOwner','Invoke-RxTrace')){
            $rxSim=$rxSim.Replace($rxFunction.Extent.Text,('function '+$rxFunction.Name+' {}'))
        }
        if($rxFunction.Name -eq 'Reload-RxTarget'){
            $rxSim=$rxSim.Replace($rxFunction.Extent.Text,@'
function Reload-RxTarget {
 $rxFake.Reloads++
 if($rxFake.Fault -eq 'first-reload' -and $rxFake.Reloads -eq 1){throw 'simulated first reload failure'}
 if($rxFake.Fault -eq 'external-conflict' -and $rxFake.Reloads -eq 1){$rxFake.Values['QCDriverConfig']=123}
}
'@)
        }
        if($rxFunction.Name -eq 'Start-RxTrace'){
            $rxSim=$rxSim.Replace($rxFunction.Extent.Text,@'
function Start-RxTrace {
 $rxTraceCalls.start++
 if($rxCase -eq 'trace-start'){throw 'simulated ETW start failure'}
 $script:rxTraceStarted=$true;$script:rxTraceStopped=$false
 if($rxCase -eq 'trace-update'){throw 'simulated ETW provider update failure'}
}
'@)
        }
        if($rxFunction.Name -eq 'Stop-RxTrace'){
            $rxSim=$rxSim.Replace($rxFunction.Extent.Text,@'
function Stop-RxTrace {
 if($script:rxTraceStarted){
  $rxTraceCalls.stop++
  if($rxCase -eq 'trace-stop'){throw 'simulated ETW stop failure'}
  $script:rxTraceStopped=$true
 }
}
'@)
        }
    }
    $rxSim=$rxSim.Replace("if(!`$rxPlan.admin){throw 'Arm requires the separately approved administrator run.'}",'# Mock only.')
    $rxSim=$rxSim.Replace('while($rxTimer.ElapsedMilliseconds -lt 300000 -and !(Test-Path -LiteralPath (Join-Path $rxControl ''restore.request''))){Start-Sleep -Milliseconds 250}','# Mock: capture has finished.')
    if($rxSim.Contains('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey') -or $rxSim.Contains('Disable-PnpDevice -InstanceId') -or $rxSim.Contains('Enable-PnpDevice -InstanceId') -or $rxSim.Contains('& $rxLogman')){throw 'Real mutation remained in mock.'}
    $rxCaught=$null
    try{& ([scriptblock]::Create($rxSim))}catch{$rxCaught=$_.Exception.Message}
    $rxStatus=Get-Content -Raw -LiteralPath (Join-Path $rxFixture 'control-first-status-01\status.json') | ConvertFrom-Json
    if($rxCase -eq 'success'){
        if($rxCaught -or $rxStatus.phase -ne 'restored' -or $rxFake.Values.Count -or $rxFake.Reloads -ne 2 -or $rxTraceCalls.start -ne 1 -or $rxTraceCalls.stop -ne 1 -or !$rxStatus.etw_stopped){throw 'Mock success failed.'}
    }elseif($rxCase -eq 'external-conflict'){
        if(!$rxCaught -or $rxStatus.phase -ne 'restore-failed' -or $rxFake.Values['QCDriverConfig'] -ne 123){throw 'External change was not preserved.'}
    }elseif($rxCase -eq 'trace-stop'){
        if(!$rxCaught -or $rxStatus.phase -ne 'restore-failed' -or $rxFake.Values.Count -or $rxStatus.etw_stopped){throw 'ETW stop failure was hidden or registry cleanup failed.'}
    }else{
        if(!$rxCaught -or $rxStatus.phase -ne 'restored' -or $rxFake.Values.Count -or !$rxStatus.etw_stopped){throw 'Failure cleanup mock failed.'}
    }
    if($rxCase -eq 'trace-update' -and $rxTraceCalls.stop -ne 1){throw 'Partially started trace was not stopped.'}
    $rxResults+=[pscustomobject]@{case=$rxCase;phase=$rxStatus.phase;sets=$rxFake.Sets;deletes=$rxFake.Deletes;reloads=$rxFake.Reloads;remaining_values=$rxFake.Values.Count;trace_start=$rxTraceCalls.start;trace_stop=$rxTraceCalls.stop;etw_stopped=$rxStatus.etw_stopped;exception=$rxCaught}
}
# Exercise the actual bounded Stop function separately through a fake logman caller.
$rxStopFunction=@($rxAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Stop-RxTrace'},$true))[0].Extent.Text
$rxStopResults=@()
foreach($rxFailures in @(0,1,3)){
    $script:rxTraceStarted=$true;$script:rxTraceStopped=$false
    $rxStopCalls=0
    function Invoke-RxTrace { param($TraceArguments) $script:rxStopCalls++;if($script:rxStopCalls -le $rxFailures){throw 'simulated native stop failure'} }
    $rxStopCaught=$null
    try{& ([scriptblock]::Create($rxStopFunction+"`nStop-RxTrace"))}catch{$rxStopCaught=$_.Exception.Message}
    if($rxFailures -lt 3){if($rxStopCaught -or !$script:rxTraceStopped -or $rxStopCalls -ne $rxFailures+1){throw 'Bounded stop recovery failed.'}}
    else{if(!$rxStopCaught -or $script:rxTraceStopped -or $rxStopCalls -ne 3){throw 'Stop failure propagation failed.'}}
    $rxStopResults+=[pscustomobject]@{initial_failures=$rxFailures;calls=$rxStopCalls;stopped=$script:rxTraceStopped;exception=$rxStopCaught}
}
if((Get-FileHash -LiteralPath $rxAdminPath).Hash -ne $rxAdminHash){throw 'Actual helper changed during mocks.'}
$rxReport=[ordered]@{admin_helper_sha256=$rxAdminHash.ToLower();parser_clean=$true;no_real_registry_or_pnp_or_etw_io=$true;no_serial_opened=$true;cases=$rxResults;bounded_stop_cases=$rxStopResults;limitations='Mocks verify control flow only. Real ETW/PnP/driver timing and interrupted process cleanup still require actual observation.'}
[IO.File]::WriteAllText((Join-Path $rxRoot 'prepared-measurement-tests.json'),($rxReport | ConvertTo-Json -Depth 7).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxReport | ConvertTo-Json -Depth 7
