# Extract actual functions only. Never invoke coordinator, PnP or GET APIs.
$ErrorActionPreference='Stop'
function Import-OnlyFunctions([string]$Path,[string[]]$Names) {
    $tokens=$null;$errors=$null
    $tree=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Candidate PowerShell syntax failed'}
    foreach($n in $tree.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)) {
        if($n.Name -in $Names){. ([scriptblock]::Create(('function global:'+ $n.Name + $n.Extent.Text.Substring(('function '+$n.Name).Length))))}
    }
}
Import-OnlyFunctions (Join-Path $PSScriptRoot 'watch-one-hub.ps1') @('Get-Usb500NcmRootHub')
Import-OnlyFunctions (Join-Path $PSScriptRoot 'host-parent.ps1') @('Read-Usb500SharedText','Convert-Usb500CaptureUtc','Get-Usb500Gate','Write-Usb500NewJson')
$script:ncm=@('USB\VID_0525&PID_A4A1\62BC28A1')
$script:parent='USB\ROOT_HUB30\FIXTURE'
$script:interface='\\?\USB#ROOT_HUB30#FIXTURE#{f18a0e88-c30c-11d0-8815-00a0c906bed8}'
function Get-PnpDevice {param([switch]$PresentOnly,[string]$InstanceId)
    if(-not $PresentOnly){throw 'Only present fixture requested'}
    if($InstanceId){return [pscustomobject]@{InstanceId=$script:parent}}
    return @($script:ncm | ForEach-Object {[pscustomobject]@{InstanceId=$_}})
}
function Get-PnpDeviceProperty {param([string]$InstanceId,[string]$KeyName)
    if($KeyName -ne 'DEVPKEY_Device_Parent'){throw 'Unexpected property'}
    return [pscustomobject]@{Type='String';Data=$script:parent}
}
function pnputil {$global:LASTEXITCODE=0;return $script:interface}
function Reject([scriptblock]$Action) {$refused=$false;try{& $Action|Out-Null}catch{$refused=$true};if(-not $refused){throw 'Expected refusal'}}
$cases=[Collections.Generic.List[string]]::new()
$topology=Get-Usb500NcmRootHub
if($topology.Interface -ne $script:interface -or $topology.HubInstance -ne $script:parent){throw 'Actual direct-root selection failed'}
$script:parent='USB\VID_05C6&PID_9500\EUD';Reject {Get-Usb500NcmRootHub}
$script:parent='USB\ROOT_HUB30\FIXTURE';$script:ncm+= 'USB\VID_0525&PID_A4A1\OTHER';Reject {Get-Usb500NcmRootHub}
$script:ncm=@('USB\VID_0525&PID_A4A1\WRONG');Reject {Get-Usb500NcmRootHub}
$script:ncm=@('USB\VID_0525&PID_A4A1\62BC28A1');$script:interface='\\?\USB#ROOT_HUB30#OTHER#{f18a0e88-c30c-11d0-8815-00a0c906bed8}';Reject {Get-Usb500NcmRootHub}
$cases.Add('actual root discovery: sole exact NCM/current parent only; EUD/duplicate/wrong serial/other root interface refused')
Add-Type -Path (Join-Path $PSScriptRoot 'UsbHubReadOnly.cs')
$node=[byte[]]::new(76);$node[4]=9;$node[5]=0x29;$node[6]=255
if([SamuraiUsb500.Decode]::Hub($node).Ports -ne 255){throw 'Root byte port bound failed'}
$port=[byte[]]::new(35);[BitConverter]::GetBytes([uint32]255).CopyTo($port,0)
$port[4]=18;$port[5]=1;$port[12]=0x25;$port[13]=5;$port[14]=0xa1;$port[15]=0xa4;$port[21]=1;$port[22]=1;$port[31]=1
if(-not [SamuraiUsb500.Decode]::Target([SamuraiUsb500.Decode]::Port($port,255))){throw 'Exact target on port255 rejected'}
Reject {[SamuraiUsb500.Decode]::Port($port,256)}
$node[6]=0;Reject {[SamuraiUsb500.Decode]::Hub($node)}
$cases.Add('actual managed decoder: root255 and exact target255 accepted; zero hub/port256 rejected; no native GET called')

$temp=Join-Path ([IO.Path]::GetTempPath()) ('usb500-r8-root-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp|Out-Null
$reader=[Diagnostics.Process]::GetCurrentProcess()
try {
 $now=[DateTimeOffset]::UtcNow
 $meta=@{ReadOnly=$true;DurationSeconds=140;PortCount=16;DirectRootHub=$true;NcmInstance='USB\VID_0525&PID_A4A1\62BC28A1';HubInstance='USB\ROOT_HUB30\FIXTURE';
   DecoderSha256=(Get-FileHash (Join-Path $PSScriptRoot 'UsbHubReadOnly.cs') -Algorithm SHA256).Hash.ToLowerInvariant();
   CollectorSha256=(Get-FileHash (Join-Path $PSScriptRoot 'watch-one-hub.ps1') -Algorithm SHA256).Hash.ToLowerInvariant()}
 $ready=@{Armed=$true;DurationSeconds=140;TargetPort=16}
 $ports=@(1..16|ForEach-Object {[pscustomobject]@{Port=$_;Utc=$now.ToString('o');Decoded=@{ExpectedPort=$_;Port=$_;Status=$(if($_ -eq 16){1}else{0});DescriptorValid=($_ -eq 16);Vendor='0525';Product='a4a1';Configuration=1;IsHub=$false}}})
 $frame=@{Armed=$true;PartialSweep=$false;Ports=$ports;PinnedTargetPort=16;StartMs=5000;EndMs=5010;Utc=$now.ToString('o');TargetMatches=@(16);Sweep=27}
 function Save-Metadata {[IO.File]::WriteAllText((Join-Path $temp 'metadata-private.json'),($meta|ConvertTo-Json))}
 Save-Metadata
 Write-Usb500NewJson (Join-Path $temp 'ready.json') $ready
 [IO.File]::WriteAllText((Join-Path $temp 'ports-private.jsonl'),(($frame|ConvertTo-Json -Depth 10 -Compress)+[Environment]::NewLine))
 $params=@{Reader=$reader;OwnedHandle=$reader.Handle.ToInt64();OwnedStartTicks=$reader.StartTime.ToUniversalTime().Ticks;OwnedPid=$reader.Id;OwnedExe=$reader.MainModule.FileName;Clock=[Diagnostics.Stopwatch]::StartNew();Directory=$temp;Nonce=('a'*48);Now=$now}
 $gate=Get-Usb500Gate @params
 if($gate.host_ready.target_port -ne 16 -or $gate.host_ready.capture_id -ne ('usb500-r8-eud-off-'+('a'*48))){throw 'Actual new parent gate rejected direct root16'}
 $cases.Add('actual owned-process parent gate accepts fresh unique direct-root16 without old port7 constraint')
 $meta.HubInstance='USB\VID_05C6&PID_9500\EUD';Save-Metadata;Reject {Get-Usb500Gate @params}
 $meta.HubInstance='USB\ROOT_HUB30\FIXTURE';$meta.CollectorSha256='31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5';Save-Metadata;Reject {Get-Usb500Gate @params}
 $cases.Add('actual parent rejects historical EUD hub metadata or old reader bytes')
 $result=@{passed=$true;cases=$cases.Count;sequences=$cases;functions_only=$true;coordinator_executed=$false;collector_executed=$false;pnputil_calls_fake=$true;native_GET_called=$false;usb_access=$false;device_access=$false;
  tested_files=@{};test_source_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()}
 foreach($n in @('host-parent.ps1','watch-one-hub.ps1','UsbHubReadOnly.cs')){$result.tested_files[$n]=(Get-FileHash (Join-Path $PSScriptRoot $n) -Algorithm SHA256).Hash.ToLowerInvariant()}
 [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'root-reader-test-result.json'),(($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
 $result|ConvertTo-Json -Depth 8
} finally {
 $reader.Dispose()
 $resolved=[IO.Path]::GetFullPath($temp)
 if([IO.Path]::GetDirectoryName($resolved) -ne [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar) -or [IO.Path]::GetFileName($resolved) -notmatch '^usb500-r8-root-[0-9a-f]{32}$'){throw 'Refuse cleanup outside owned fixture temp'}
 Remove-Item -LiteralPath $resolved -Recurse -Force
}
