# Offline replay only: compile the frozen decoder and call Decode.Hub/Port.
# Never construct HubSession, open a USB handle, or call a native GET.
$ErrorActionPreference='Stop'
$trial='E:/edk2-samurai-out/charging-management-20261023/usb500-r7-18306f77ab5726a7929b99d2131242353f7a7c45a1f69e24'
$source=Join-Path (Split-Path $PSScriptRoot) 'usb500-r7-candidate/UsbHubReadOnly.cs'
$digest=(Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant()
if($digest -ne '9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716'){throw 'Frozen decoder differs'}
Add-Type -Path $source
$meta=Get-Content -LiteralPath (Join-Path $trial 'host-reader/metadata-private.json') -Raw | ConvertFrom-Json
$hub=[SamuraiUsb500.Decode]::Hub([Convert]::FromBase64String($meta.NodeBase64))
$rows=0;$frames=0;$statuses=@{};$zeroAbsent=0
$fields=@('Port','ExpectedPort','ReturnedIndex','EmpiricalZeroAbsent','Status','StatusName','EvidenceClass','Vendor','Product','Configuration','Speed','IsHub','Address','OpenPipes','DescriptorValid','DescriptorWarning')
foreach($line in [IO.File]::ReadLines((Join-Path $trial 'host-reader/ports-private.jsonl'))){
 if([string]::IsNullOrWhiteSpace($line)){throw 'Empty host frame'}
 $frame=$line|ConvertFrom-Json;$frames++
 foreach($port in $frame.Ports){
  if($port.PSObject.Properties['Error']){throw 'Original query error'}
  $fresh=[SamuraiUsb500.Decode]::Port([Convert]::FromBase64String($port.RawBase64),[uint32]$port.Port)
  foreach($field in $fields){if($fresh.$field -cne $port.Decoded.$field){throw "Cached decoded field mismatch: sweep$($frame.Sweep) port$($port.Port) $field"}}
  if($fresh.EmpiricalZeroAbsent){$zeroAbsent++}
  $key="$($fresh.Port):$($fresh.StatusName)"
  if(-not $statuses.ContainsKey($key)){$statuses[$key]=0};$statuses[$key]++
  $rows++
 }
}
$result=@{passed=$true;scope='cached original GET bytes replayed through the exact frozen static decoder';sweeps=$frames;responses=$rows;all_decoded_fields_match=$true;zero_absent_responses=$zeroAbsent;hub_ports=$hub.Ports;hub_bus_powered=$hub.BusPowered;status_counts=$statuses;decoder_sha256=$digest;host_capture_sha256=(Get-FileHash (Join-Path $trial 'host-reader/ports-private.jsonl') -Algorithm SHA256).Hash.ToLowerInvariant();metadata_sha256=(Get-FileHash (Join-Path $trial 'host-reader/metadata-private.json') -Algorithm SHA256).Hash.ToLowerInvariant();usb_handles_opened=0;ioctls_issued=0;frozen62_suite_rerun=$false}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'raw-redecode-result.json'),(($result|ConvertTo-Json -Depth 8)+"`n"),[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Depth 8
