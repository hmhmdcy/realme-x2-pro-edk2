"""Prepare a fresh, separately approved ETW + driver logger experiment."""
from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parent
old = root.parent/'rx57/driver-log-admin-02.ps1'
assert sha256(old.read_bytes()).hexdigest() == 'e852757856071be4c1cd4cad3956d564472b051b6672c622e5fb034f2dbd0ec7'
s = old.read_text(encoding='utf-8-sig')

def replace(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

replace("$rxRoot='E:\\edk2-samurai-out\\rx57'", "$rxRoot='E:\\edk2-samurai-out\\rx58'")
replace("$rxControl=Join-Path $rxRoot 'control-02'", "$rxControl=Join-Path $rxRoot 'control-first-status-01'")
replace("$rxLogDir=Join-Path $rxRoot 'driver-logs-02'", "$rxLogDir=Join-Path $rxRoot 'driver-logs-first-status-01'")
replace("$rxRestoreFailure=$null", """$rxRestoreFailure=$null
$rxTraceStarted=$false
$rxTraceStopped=$true
$rxTraceSession='EUD-RX58-FIRST-STATUS-01-'+$PID
$rxTraceOut=Join-Path $rxRoot 'first-status-01.etl'
$rxTraceLog=Join-Path $rxRoot 'first-status-01.trace-log.txt'
$rxLogman=Join-Path $env:SystemRoot 'System32\\logman.exe'
function Invoke-RxTrace([string[]]$TraceArguments) {
    $rxTraceReply=& $rxLogman @TraceArguments 2>&1
    $rxTraceCode=$LASTEXITCODE
    $rxTraceReply | Out-File -LiteralPath $rxTraceLog -Append -Encoding utf8
    if($rxTraceCode -ne 0){throw "USB ETW command failed: $rxTraceCode"}
}
function Start-RxTrace {
    if(Test-Path -LiteralPath $rxTraceOut){throw 'Fresh ETL already exists.'}
    $rxTraceReply=& $rxLogman start $rxTraceSession -p Microsoft-Windows-USB-USBXHCI 0x81 -o $rxTraceOut -f bincirc -max 64 -nb 16 64 -bs 64 -ets 2>&1
    $rxTraceCode=$LASTEXITCODE
    # Cleanup becomes mandatory immediately after native start succeeds.
    $script:rxTraceStarted=$rxTraceCode -eq 0
    $script:rxTraceStopped=!$script:rxTraceStarted
    $rxTraceReply | Out-File -LiteralPath $rxTraceLog -Append -Encoding utf8
    if(!$script:rxTraceStarted){throw "USB ETW start failed: $rxTraceCode"}
    Invoke-RxTrace -TraceArguments @('update',$rxTraceSession,'-p','Microsoft-Windows-USB-UCX','0x81','-ets')
    Invoke-RxTrace -TraceArguments @('update',$rxTraceSession,'-p','Microsoft-Windows-USB-USBHUB3','0x1','-ets')
}
function Stop-RxTrace {
    if($script:rxTraceStarted){
        $rxStopError=$null
        foreach($rxStopTry in 1..3){
            try {
                Invoke-RxTrace -TraceArguments @('stop',$rxTraceSession,'-ets')
                $script:rxTraceStopped=$true
                return
            } catch {$rxStopError=$_;Start-Sleep -Milliseconds 250}
        }
        throw $rxStopError
    }
}""")
replace(r"rx57[\\/]capture-windows(?:-02)?\.ps1", r"rx(?:57|58)[\\/]capture-windows(?:-02|-first-status)?\.ps1")
replace("no_etw=$true", "no_etw=$false;etw_session=$rxTraceSession;etw_max_mb=64;etw_providers=@('USBXHCI:0x81','UCX:0x81','USBHUB3:0x1');serial_owner_count=3;data_commands_only_in_final_owner=$true")
replace("'logging-plan-02.json'", "'measurement-plan-01.json'")
replace("    Reload-RxTarget\n    Write-RxJson", "    Reload-RxTarget\n    Start-RxTrace\n    Write-RxJson")
replace("registry_enabled=$true;driver_reloaded=$true;capture_start", "registry_enabled=$true;driver_reloaded=$true;etw_started=$rxTraceStarted;etw_session=$rxTraceSession;capture_start")
replace("finally {\n    try {\n        if($rxKey)", """finally {
    try {Stop-RxTrace} catch {$rxRestoreFailure=$_.Exception.Message}
    try {
        if($rxKey)""")
replace("targeted_original_values_absent=(!$rxRestoreFailure);registry_touched", "targeted_original_values_absent=(!$rxRestoreFailure);etw_stopped=$rxTraceStopped;etw_session=$rxTraceSession;registry_touched")
(root/'driver-log-etw-admin.ps1').write_text(s, encoding='utf-8')
for name in ('eud-terminal-rx-perf.ps1', 'EudRxAudit.cs', 'EudSerialPerf.cs'):
    (root/name).write_bytes((root.parent/'rx57'/name).read_bytes())
print(sha256((root/'driver-log-etw-admin.ps1').read_bytes()).hexdigest())
