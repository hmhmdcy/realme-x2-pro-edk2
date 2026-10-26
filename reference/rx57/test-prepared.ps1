$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx57'
$rxScriptPath=Join-Path $rxRoot 'driver-log-admin.ps1'
$rxBeforeHash=(Get-FileHash -LiteralPath $rxScriptPath).Hash
$rxSource=[IO.File]::ReadAllText($rxScriptPath)
$rxTokens=$null;$rxParseErrors=$null
$rxAst=[Management.Automation.Language.Parser]::ParseInput($rxSource,[ref]$rxTokens,[ref]$rxParseErrors)
if($rxParseErrors.Count){throw 'Administrator script parse failed.'}
foreach($rxFile in @('capture-windows.ps1','launch-approved-logger.ps1')){
    $rxAstOther=[Management.Automation.Language.Parser]::ParseFile((Join-Path $rxRoot $rxFile),[ref]$rxTokens,[ref]$rxParseErrors)
    if($rxParseErrors.Count){throw "$rxFile parse failed."}
}
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using Microsoft.Win32;
public sealed class Rx57FakeRegistry {
 public Dictionary<string,object> Values = new Dictionary<string,object>();
 public int Sets, Deletes, Reloads;
 public string Fault;
 public Rx57FakeRegistry(string fault) { Fault=fault; }
 public Rx57FakeKey OpenReadKey() { return new Rx57FakeKey(this,false); }
 public Rx57FakeKey OpenWriteKey() { return new Rx57FakeKey(this,true); }
}
public sealed class Rx57FakeKey : IDisposable {
 Rx57FakeRegistry Parent; bool Write;
 public Rx57FakeKey(Rx57FakeRegistry parent,bool write) { Parent=parent; Write=write; }
 public string[] GetValueNames() { var a=new string[Parent.Values.Count]; Parent.Values.Keys.CopyTo(a,0); return a; }
 public object GetValue(string n,object d,RegistryValueOptions o) { object v; return Parent.Values.TryGetValue(n,out v)?v:d; }
 public RegistryValueKind GetValueKind(string n) { return Parent.Values[n] is int?RegistryValueKind.DWord:RegistryValueKind.String; }
 public void SetValue(string n,object v,RegistryValueKind k) {
  if(!Write)throw new Exception("readonly fake key");
  Parent.Sets++;
  if(Parent.Fault=="second-write" && Parent.Sets==2)throw new Exception("simulated second write failure");
  Parent.Values[n]=v;
 }
 public void DeleteValue(string n,bool missing) { Parent.Deletes++; Parent.Values.Remove(n); }
 public void Flush() {}
 public void Dispose() {}
}
'@
$rxRunId=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff')
$rxResults=@()
foreach($rxCase in @('success','second-write','first-reload','external-conflict')){
    $rxFixture=Join-Path $rxRoot ('mock-'+$rxRunId+'-'+$rxCase)
    [IO.Directory]::CreateDirectory($rxFixture) | Out-Null
    $rxFake=[Rx57FakeRegistry]::new($rxCase)
    $rxSim=$rxSource.Replace("param([ValidateSet('Plan','Arm')][string]`$Mode='Plan')","`$Mode='Arm'")
    $rxSim=$rxSim.Replace("`$rxRoot='E:\edk2-samurai-out\rx57'","`$rxRoot='$rxFixture'")
    $rxSim=$rxSim.Replace('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$false)','$rxFake.OpenReadKey()')
    $rxSim=$rxSim.Replace('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($rxSubKey,$true)','$rxFake.OpenWriteKey()')
    foreach($rxFunction in $rxAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){
        if($rxFunction.Name -in @('Assert-RxIdentity','Assert-RxNoOwner')){
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
    }
    $rxSim=$rxSim.Replace("if(!`$rxPlan.admin){throw 'Arm requires the separately approved administrator run.'}",'# Simulation only; no native administrator action.')
    $rxSim=$rxSim.Replace('while($rxTimer.ElapsedMilliseconds -lt 300000 -and !(Test-Path -LiteralPath (Join-Path $rxControl ''restore.request''))){Start-Sleep -Milliseconds 250}','# Simulation: capture finished immediately.')
    if($rxSim.Contains('[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey') -or $rxSim.Contains('Disable-PnpDevice -InstanceId') -or $rxSim.Contains('Enable-PnpDevice -InstanceId')){throw 'Native mutation remained in mock script.'}
    $rxCaught=$null
    try{& ([scriptblock]::Create($rxSim))}catch{$rxCaught=$_.Exception.Message}
    $rxStatus=Get-Content -Raw -LiteralPath (Join-Path $rxFixture 'control-01\status.json') | ConvertFrom-Json
    if($rxCase -eq 'success'){
        if($rxCaught -or $rxStatus.phase -ne 'restored' -or $rxFake.Values.Count -or $rxFake.Reloads -ne 2){throw 'Success/restore mock failed.'}
    }elseif($rxCase -eq 'external-conflict'){
        if(!$rxCaught -or $rxStatus.phase -ne 'restore-failed' -or $rxFake.Values['QCDriverConfig'] -ne 123){throw 'External change was not preserved.'}
    }else{
        if(!$rxCaught -or $rxStatus.phase -ne 'restored' -or $rxFake.Values.Count){throw 'Failure cleanup mock failed.'}
    }
    $rxResults+= [pscustomobject]@{case=$rxCase;phase=$rxStatus.phase;sets=$rxFake.Sets;deletes=$rxFake.Deletes;reloads=$rxFake.Reloads;remaining_values=$rxFake.Values.Count;exception=$rxCaught}
}
if((Get-FileHash -LiteralPath $rxScriptPath).Hash -ne $rxBeforeHash){throw 'Actual helper changed during mock tests.'}
$rxReloadFunction=@($rxAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Reload-RxTarget'},$true))
if($rxReloadFunction.Count -ne 1){throw 'Reload function binding failed.'}
$rxReloadResults=@()
foreach($rxReloadCase in @('success','disable-error','enable-error')){
    $rxReloadCounters=@{disable=0;enable=0}
    $rxReloadSim=@'
function Assert-RxNoOwner {}
function Assert-RxIdentity {}
function Disable-PnpDevice { param($InstanceId,[switch]$Confirm,[switch]$PassThru,$ErrorAction)
 $rxReloadCounters.disable++
 if($rxReloadCase -eq 'disable-error'){throw 'simulated disable error'}
 return 0
}
function Enable-PnpDevice { param($InstanceId,[switch]$Confirm,[switch]$PassThru,$ErrorAction)
 $rxReloadCounters.enable++
 if($rxReloadCase -eq 'enable-error'){return 5}
 return 0
}
'@ + "`n" + $rxReloadFunction[0].Extent.Text + "`nReload-RxTarget"
    $rxReloadCaught=$null
    try{& ([scriptblock]::Create($rxReloadSim))}catch{$rxReloadCaught=$_.Exception.Message}
    if($rxReloadCounters.disable -ne 1 -or $rxReloadCounters.enable -ne 1){throw 'Disable/enable mock counts failed.'}
    if(($rxReloadCase -eq 'success') -ne ($null -eq $rxReloadCaught)){throw 'Reload error propagation failed.'}
    $rxReloadResults+=[pscustomobject]@{case=$rxReloadCase;disable=$rxReloadCounters.disable;enable=$rxReloadCounters.enable;exception=$rxReloadCaught}
}
$rxReport=[ordered]@{mock_registry_only=$true;no_native_pnp_calls=$true;no_port_opened=$true;actual_helper_sha256=$rxBeforeHash.ToLower();parser_clean=$true;cases=$rxResults;reload_cases=$rxReloadResults;not_tested='Real PnP/registry failures, actual driver log creation, actual scheduling/deadlines and process termination are not verified by mocks.'}
[IO.File]::WriteAllText((Join-Path $rxRoot 'prepared-tests.json'),($rxReport | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxReport | ConvertTo-Json -Depth 6
