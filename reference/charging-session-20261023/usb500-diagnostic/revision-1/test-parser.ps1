# Offline only: compile native declarations, invoke ONLY byte-array decoder.
# No HubSession construction, PnP enumeration or DeviceIoControl call.
$ErrorActionPreference='Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'UsbHubReadOnly.cs')
$parserCases=[System.Collections.Generic.List[string]]::new()
function Assert-Case([bool]$Value,[string]$Name) {
    if (-not $Value) { throw ('Failed offline case: '+$Name) }
    $parserCases.Add($Name)
}
function Reject-Case([scriptblock]$Action,[string]$Name) {
    $rejected=$false
    try { & $Action | Out-Null } catch { $rejected=$true }
    Assert-Case $rejected $Name
}
function Hub-Bytes {
    $b=[byte[]]::new(76);$b[4]=9;$b[5]=0x29;$b[6]=7;$b[75]=1
    return ,$b
}
function Port-Bytes([uint32]$Status=1,[uint32]$Index=3,[int]$Size=35) {
    $b=[byte[]]::new($Size)
    [BitConverter]::GetBytes($Index).CopyTo($b,0)
    $b[4]=18;$b[5]=1
    [BitConverter]::GetBytes([uint16]0x0525).CopyTo($b,12)
    [BitConverter]::GetBytes([uint16]0xa4a1).CopyTo($b,14)
    $b[21]=1;$b[22]=1;$b[23]=2;$b[24]=0
    [BitConverter]::GetBytes([uint16]4).CopyTo($b,25)
    [BitConverter]::GetBytes($Status).CopyTo($b,31)
    return ,$b
}

$hub=[SamuraiUsb500.Decode]::Hub((Hub-Bytes))
Assert-Case ($hub.Ports -eq 7 -and $hub.BusPowered -and $hub.ControllerCurrentMa -eq 0) 'known-EUD-layout-76-byte-pack1'
foreach ($length in @(0,35,75,77)) {
    $raw=[byte[]]::new($length)
    Reject-Case { [SamuraiUsb500.Decode]::Hub($raw) } ('node-size-'+$length)
}
foreach ($fault in @('node_union','type','descriptor_short','port0','port16','boolean2')) {
    $raw=Hub-Bytes
    switch ($fault) {
        'node_union' { $raw[0]=1 }
        'type' { $raw[5]=0x2a }
        'descriptor_short' { $raw[4]=8 }
        'port0' { $raw[6]=0 }
        'port16' { $raw[6]=16 }
        'boolean2' { $raw[75]=2 }
    }
    Reject-Case { [SamuraiUsb500.Decode]::Hub($raw) } ('node-reject-'+$fault)
}

$statusNames=@('NoDeviceConnected','DeviceConnected','DeviceFailedEnumeration','DeviceGeneralFailure',
    'DeviceCausedOvercurrent','DeviceNotEnoughPower','DeviceNotEnoughBandwidth','DeviceHubNestedTooDeeply',
    'DeviceInLegacyHub','DeviceEnumerating','DeviceReset')
for ($status=0;$status -lt $statusNames.Count;$status++) {
    $decoded=[SamuraiUsb500.Decode]::Port((Port-Bytes $status),3)
    Assert-Case ($decoded.Status -eq $status -and $decoded.StatusName -eq $statusNames[$status]) ('connection-status-'+$statusNames[$status])
}
$raw=Port-Bytes 5
$decoded=[SamuraiUsb500.Decode]::Port($raw,3)
Assert-Case ($decoded.Status -eq 5 -and $decoded.EvidenceClass -eq 'explicit_host_power_rejection' -and [BitConverter]::ToUInt32(($raw+[byte]0),32) -eq 0) 'status-offset31-not-default-aligned32'
$serialized=$decoded | ConvertTo-Json | ConvertFrom-Json
Assert-Case ($serialized.Status -eq 5 -and $serialized.EvidenceClass -eq 'explicit_host_power_rejection' -and $serialized.Port -eq 3) 'actual-log-serialization-keeps-status-port-and-class'
Assert-Case ([SamuraiUsb500.Decode]::Evidence(2) -eq 'enumeration_failure' -and [SamuraiUsb500.Decode]::Evidence(3) -eq 'general_failure') 'generic-enumeration-failure-is-not-power-proof'
$decoded=[SamuraiUsb500.Decode]::Port((Port-Bytes ([uint32]::MaxValue)),3)
Assert-Case ($decoded.StatusName -eq 'Unknown(4294967295)' -and $decoded.EvidenceClass -eq 'unknown_status') 'future-unknown-status-preserved-not-guessed'

$raw=Port-Bytes 1
$decoded=[SamuraiUsb500.Decode]::Port($raw,3)
Assert-Case ($decoded.Port -eq 3 -and $decoded.Vendor -eq '0525' -and $decoded.Product -eq 'a4a1' -and $decoded.Configuration -eq 1 -and $decoded.Address -eq 4) 'all-pack1-fields-at-verified-offsets'
Assert-Case ([SamuraiUsb500.Decode]::Target($decoded)) 'configured-NCM-child-match'
foreach ($fault in @('unconfigured','otherconfig','disconnected','hub','wrongpid','descriptor','zero_config_count')) {
    $raw=Port-Bytes 1
    switch ($fault) {
        'unconfigured' { $raw[22]=0 }
        'otherconfig' { $raw[22]=2 }
        'disconnected' { $raw[31]=0 }
        'hub' { $raw[24]=1 }
        'wrongpid' { $raw[14]=0 }
        'descriptor' { $raw[4]=0 }
        'zero_config_count' { $raw[21]=0 }
    }
    $decoded=[SamuraiUsb500.Decode]::Port($raw,3)
    Assert-Case (-not [SamuraiUsb500.Decode]::Target($decoded)) ('not-NCM-match-'+$fault)
}
$raw=[byte[]]::new(35);[BitConverter]::GetBytes([uint32]3).CopyTo($raw,0)
$raw[31]=5
$decoded=[SamuraiUsb500.Decode]::Port($raw,3)
Assert-Case ($decoded.Status -eq 5 -and -not $decoded.DescriptorValid -and $decoded.Vendor -eq '0000') 'power-status-retained-when-enumeration-lost-VIDPID'
foreach ($length in @(0,34,513)) {
    $raw=[byte[]]::new($length)
    Reject-Case { [SamuraiUsb500.Decode]::Port($raw,3) } ('connection-size-'+$length)
}
$raw=Port-Bytes
Reject-Case { [SamuraiUsb500.Decode]::Port($raw,4) } 'returned-connection-index-mismatch'
Reject-Case { [SamuraiUsb500.Decode]::Port($raw,0) } 'requested-port-zero'
Reject-Case { [SamuraiUsb500.Decode]::Port($raw,16) } 'requested-port-outside-bounded-hub'
$raw[24]=2
Reject-Case { [SamuraiUsb500.Decode]::Port($raw,3) } 'invalid-device-is-hub-boolean'
foreach ($pipes in @([uint32]1,[uint32]44,[uint32]::MaxValue)) {
    $raw=Port-Bytes
    [BitConverter]::GetBytes($pipes).CopyTo($raw,27)
    Reject-Case { [SamuraiUsb500.Decode]::Port($raw,3) } ('truncated-or-overflow-pipes-'+$pipes)
}
$raw=Port-Bytes 1 3 46
[BitConverter]::GetBytes([uint32]1).CopyTo($raw,27)
Assert-Case (([SamuraiUsb500.Decode]::Port($raw,3)).OpenPipes -eq 1) 'one-packed-11-byte-pipe'
foreach ($code in @([uint32]0,[uint32]0x220444,[uint32]::MaxValue)) {
    Reject-Case { [SamuraiUsb500.Decode]::Allowed($code) } ('non-GET-IOCTL-refused-'+$code)
}
[SamuraiUsb500.Decode]::Allowed(0x220408);[SamuraiUsb500.Decode]::Allowed(0x220448)
Assert-Case $true 'exact-two-GET-allowlist'

# Parse the collector syntax without invoking it. Also check its hub-interface
# regex against the previous real private capture; no PnP/hub query occurs.
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'watch-one-hub.ps1'),[ref]$tokens,[ref]$errors)
Assert-Case ($errors.Count -eq 0) 'collector-powershell-syntax'
$watchdogTokens=$null;$watchdogErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'start-bounded-watch.ps1'),[ref]$watchdogTokens,[ref]$watchdogErrors) | Out-Null
Assert-Case ($watchdogErrors.Count -eq 0) 'watchdog-powershell-syntax-no-execution'
$regexNode=$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.StringConstantExpressionAst] -and $node.Value -like '*VID_05C6&PID_9500#*'},$true)
if ($regexNode.Count -ne 1) { throw 'Exact interface regex fixture selection' }
$privateRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../edk2-samurai-out/charging-management-20261023'))
$observed=Get-Content -Raw -LiteralPath (Join-Path $privateRoot 'host-usb-topology/eud-hub-private.json') | ConvertFrom-Json
$matches=[regex]::Matches($observed.Interface,$regexNode[0].Value,'IgnoreCase')
Assert-Case ($matches.Count -eq 1 -and $matches[0].Value -eq $observed.Interface) 'exact-old-observed-EUD-interface-regex'

$main=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../charging-management-20261023'))
$sourceReceipt=Get-Content -Raw -LiteralPath (Join-Path $main 'usb-host-hub-result.json') | ConvertFrom-Json
$headers=[ordered]@{}
foreach ($name in @('usbspec.h','usbiodef.h','usbioctl.h')) {
    $actual=(Get-FileHash (Join-Path 'C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/shared' $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $sourceReceipt.source_headers.$name) { throw ('Different Windows SDK header: '+$name) }
    $headers[$name]=$actual
}
$tested=[ordered]@{}
foreach ($name in @('UsbHubReadOnly.cs','watch-one-hub.ps1','start-bounded-watch.ps1','test-parser.ps1')) {
    $tested[$name]=(Get-FileHash (Join-Path $PSScriptRoot $name) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$audited=[ordered]@{}
foreach ($name in @('query-usb-hub.ps1','usb-reenumerate.py','run-usb-reenumerate.py')) {
    $audited[$name]=(Get-FileHash (Join-Path $main $name) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$result=[ordered]@{ Passed=$true; Cases=$parserCases.Count; CaseNames=$parserCases.ToArray(); TestedFiles=$tested
    AuditedMainFiles=$audited; WindowsSdkHeaders=$headers; WindowsSdkHeadersReadOnly=$true
    PhoneAccessed=$false; CameraSdkAccessed=$false; MainOrSdkModified=$false; HardwareQueriesExecuted=$false
    Scope='Actual C# byte-array parser/allowlist + PowerShell AST/interface regex; no native session or DeviceIoControl invoked' }
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'test-result.json') -Encoding utf8
[pscustomobject]$result | Select-Object Passed,Cases,TestedFiles,HardwareQueriesExecuted | ConvertTo-Json -Depth 5
