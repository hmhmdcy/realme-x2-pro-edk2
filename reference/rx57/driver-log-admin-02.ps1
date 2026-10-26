param([ValidateSet('Plan','Arm')][string]$Mode='Plan')
$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx57'
$rxInstance='USB\VID_05C6&PID_9505\8&5580DC5&0&5'
$rxClass='{4d36e978-e325-11ce-bfc1-08002be10318}\0008'
$rxSubKey='SYSTEM\CurrentControlSet\Control\Class\'+$rxClass
$rxControl=Join-Path $rxRoot 'control-02'
$rxLogDir=Join-Path $rxRoot 'driver-logs-02'
$rxNtLogDir='\??\'+$rxLogDir
$rxNames=@('QCDriverConfig','QCDriverLoggingDirectory')
$rxEncoding=[Text.UTF8Encoding]::new($false)
$rxKey=$null
$rxTouched=@()
$rxFailure=$null
$rxRestoreFailure=$null

function Write-RxJson([string]$Path,$Value) {
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 7).Replace("`r`n","`n")+"`n",$rxEncoding)
}
function Assert-RxIdentity {
    $rxNode=Get-PnpDevice -InstanceId $rxInstance -ErrorAction Stop
    if($rxNode.Status -ne 'OK' -or $rxNode.FriendlyName -notmatch '\(COM14\)$'){throw 'Target is not the expected healthy COM14 device.'}
    $rxEnum=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\'+$rxInstance)
    if($rxEnum.Driver -ne $rxClass -or $rxEnum.Service -ne 'qcusbser'){throw 'Target driver/class changed.'}
    $rxVersion=(Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\'+$rxSubKey)).DriverVersion
    if($rxVersion -ne '2.1.3.5'){throw 'Installed driver version changed.'}
    $rxService=Get-CimInstance Win32_SystemDriver -Filter "Name='qcusbser'"
    $rxInstalledPath=Join-Path $env:windir 'System32\drivers\qcusbser.sys'
    if($rxService.State -ne 'Running' -or $rxService.PathName -ne $rxInstalledPath){throw 'Installed driver service/path changed.'}
    if((Get-FileHash -LiteralPath $rxInstalledPath).Hash.ToLower() -ne 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'){throw 'Installed service binary changed.'}
    if((Get-FileHash -LiteralPath 'E:\eud-host\qud_cab\qcusbser.sys').Hash.ToLower() -ne 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'){throw 'Driver evidence file changed.'}
}
function Assert-RxNoOwner {
    $rxOwners=@(Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and ($_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|rx57[\\/]capture-windows(?:-02)?\.ps1')
    })
    if($rxOwners.Count){throw 'A known serial/USB capture process is still alive.'}
    $rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
    if($LASTEXITCODE -ne 0 -or $rxUsb -notmatch '(?m)^6-5\s+05c6:9505\s+.*Shared\s*$' -or $rxUsb -match '(?m)^6-5\s+.*Attached'){throw '9505 USB ownership changed.'}
}
function Reload-RxTarget {
    Assert-RxNoOwner
    $rxDisableError=$null
    try {
        Disable-PnpDevice -InstanceId $rxInstance -Confirm:$false -ErrorAction Stop | Out-Null
        $rxDisabledWait=[Diagnostics.Stopwatch]::StartNew()
        while($true){
            $rxDisabledNode=Get-PnpDevice -InstanceId $rxInstance -ErrorAction Stop
            if([int]$rxDisabledNode.ConfigManagerErrorCode -eq 22){break}
            if($rxDisabledWait.ElapsedMilliseconds -ge 5000){throw 'Exact COM14 instance did not become disabled (CM_PROB_DISABLED=22).'}
            Start-Sleep -Milliseconds 250
        }
    } catch { $rxDisableError=$_ }
    finally {
        # Re-enable this exact leaf even if disabling failed or raised an error.
        Enable-PnpDevice -InstanceId $rxInstance -Confirm:$false -ErrorAction Stop | Out-Null
    }
    if($rxDisableError){throw $rxDisableError}
    $rxIdentityWait=[Diagnostics.Stopwatch]::StartNew()
    while($true){
        try {Assert-RxIdentity;break}
        catch {if($rxIdentityWait.ElapsedMilliseconds -ge 15000){throw};Start-Sleep -Milliseconds 250}
    }
}

Assert-RxIdentity
Assert-RxNoOwner
$rxReadKey=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$false)
if(!$rxReadKey){throw 'Exact device software key unavailable.'}
try {
    $rxPresent=@($rxReadKey.GetValueNames())
    $rxSlots=@(foreach($rxName in $rxNames){[pscustomobject]@{name=$rxName;present=($rxPresent -contains $rxName);kind=if($rxPresent -contains $rxName){$rxReadKey.GetValueKind($rxName).ToString()}else{$null};value=$rxReadKey.GetValue($rxName,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)}})
} finally {$rxReadKey.Dispose()}
if(@($rxSlots | Where-Object present).Count){throw 'Logging settings are no longer absent; prepare a new reviewed baseline.'}
$rxPlan=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o');mode=$Mode;admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);instance=$rxInstance;software_key=$rxSubKey;original=$rxSlots;proposed_config_hex='80000000';proposed_config_kind='DWord';proposed_directory=$rxNtLogDir;proposed_directory_kind='String';target_reload_count=2;helper_deadline_seconds=300;capture_must_start_within_seconds=60;capture_deadline_seconds=180;no_phone_flash_or_reboot=$true;no_driver_install=$true;no_etw=$true}
if($Mode -eq 'Plan'){
    Write-RxJson (Join-Path $rxRoot 'logging-plan-02.json') $rxPlan
    $rxPlan | ConvertTo-Json -Depth 7
    return
}
if(!$rxPlan.admin){throw 'Arm requires the separately approved administrator run.'}
if(Test-Path -LiteralPath $rxControl){throw 'Control directory already exists; this attempt cannot be repeated.'}
if(Test-Path -LiteralPath $rxLogDir){throw 'Log directory already exists; preserve it and prepare a new attempt.'}
[IO.Directory]::CreateDirectory($rxControl) | Out-Null
[IO.Directory]::CreateDirectory($rxLogDir) | Out-Null
Write-RxJson (Join-Path $rxControl 'backup.json') $rxPlan
$rxTimer=[Diagnostics.Stopwatch]::StartNew()
try {
    $rxKey=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$true)
    if(!$rxKey){throw 'Cannot write the exact device software key.'}
    if(@($rxKey.GetValueNames() | Where-Object {$_ -in $rxNames}).Count){throw 'Logging configuration changed after preflight.'}
    # Mark before each write: finally also handles an exception during SetValue.
    $rxTouched+= 'QCDriverConfig'
    $rxKey.SetValue('QCDriverConfig',[int]::MinValue,[Microsoft.Win32.RegistryValueKind]::DWord)
    $rxTouched+= 'QCDriverLoggingDirectory'
    $rxKey.SetValue('QCDriverLoggingDirectory',$rxNtLogDir,[Microsoft.Win32.RegistryValueKind]::String)
    $rxKey.Flush()
    Reload-RxTarget
    Write-RxJson (Join-Path $rxControl 'status.json') @{phase='ready';pid=$PID;utc=(Get-Date).ToUniversalTime().ToString('o');helper_elapsed_ms=$rxTimer.ElapsedMilliseconds;registry_enabled=$true;driver_reloaded=$true;capture_start_limit_seconds=60;capture_max_seconds=180}
    while($rxTimer.ElapsedMilliseconds -lt 300000 -and !(Test-Path -LiteralPath (Join-Path $rxControl 'restore.request'))){Start-Sleep -Milliseconds 250}
    # A finished diagnostic process may need a few seconds to exit its host shell.
    $rxSettle=[Diagnostics.Stopwatch]::StartNew()
    while($rxSettle.ElapsedMilliseconds -lt 15000){
        try {Assert-RxNoOwner;break} catch {Start-Sleep -Milliseconds 250}
    }
    Assert-RxNoOwner
} catch {$rxFailure=$_.Exception.Message}
finally {
    try {
        if($rxKey){
            $rxConflicts=@()
            foreach($rxName in $rxTouched){
                $rxCurrent=$rxKey.GetValue($rxName,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                $rxExpected=if($rxName -eq 'QCDriverConfig'){[int]::MinValue}else{$rxNtLogDir}
                if($null -ne $rxCurrent -and $rxCurrent -ne $rxExpected){$rxConflicts+=$rxName}
                else {$rxKey.DeleteValue($rxName,$false)}
            }
            $rxKey.Flush()
            if($rxConflicts.Count){throw ('Restore conflict: external changes preserved: '+($rxConflicts -join ', '))}
            foreach($rxName in $rxNames){if(@($rxKey.GetValueNames()) -contains $rxName){throw "Restore verification failed: $rxName"}}
        }
        if($rxTouched.Count){Reload-RxTarget}
    } catch {$rxRestoreFailure=$_.Exception.Message}
    finally {if($rxKey){$rxKey.Dispose()}}
    Write-RxJson (Join-Path $rxControl 'status.json') @{phase=if($rxRestoreFailure){'restore-failed'}else{'restored'};pid=$PID;utc=(Get-Date).ToUniversalTime().ToString('o');helper_elapsed_ms=$rxTimer.ElapsedMilliseconds;failure=$rxFailure;restore_failure=$rxRestoreFailure;targeted_original_values_absent=(!$rxRestoreFailure);registry_touched=$rxTouched;restore_request_seen=(Test-Path -LiteralPath (Join-Path $rxControl 'restore.request'))}
}
if($rxFailure -or $rxRestoreFailure){throw "Capture setup/result: $rxFailure; restore: $rxRestoreFailure"}
