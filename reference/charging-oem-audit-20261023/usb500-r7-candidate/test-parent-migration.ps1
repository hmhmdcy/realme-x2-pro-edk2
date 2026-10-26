# Three directed tests of actual R7 parent gate; no coordinator/USB/WSL/SSH.
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'host-parent.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'R7 parent syntax failed'}
foreach($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in @('Read-Usb500SharedText','Convert-Usb500CaptureUtc','Get-Usb500Gate','Write-Usb500NewJson')},$true)){Invoke-Expression $node.Extent.Text}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('usb500-r7-parent-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$reader=[Diagnostics.Process]::GetCurrentProcess()
try{
 $now=[DateTimeOffset]::UtcNow
 $meta=@{ReadOnly=$true;DurationSeconds=140;PortCount=7;DecoderSha256='9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716';CollectorSha256='31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5'}
 $ready=@{Armed=$true;DurationSeconds=140;TargetPort=7}
 $ports=@(1..7 | ForEach-Object {[pscustomobject]@{Port=$_;Utc=$now.ToString('o');Decoded=[pscustomobject]@{ExpectedPort=$_;Port=$_;Status=$(if($_ -eq 7){1}else{0});DescriptorValid=($_ -eq 7);Vendor='0525';Product='a4a1';Configuration=1;IsHub=$false}}})
 $frame=@{Armed=$true;PartialSweep=$false;Ports=$ports;PinnedTargetPort=7;StartMs=5000;EndMs=5010;Utc=$now.ToString('o');TargetMatches=@(7);Sweep=27}
 Write-Usb500NewJson (Join-Path $temp 'metadata-private.json') $meta
 Write-Usb500NewJson (Join-Path $temp 'ready.json') $ready
 function SaveFrame{[IO.File]::WriteAllText((Join-Path $temp 'ports-private.jsonl'),(($frame|ConvertTo-Json -Depth 10 -Compress)+"`n"))}
 SaveFrame
 $params=@{Reader=$reader;OwnedHandle=$reader.Handle.ToInt64();OwnedStartTicks=$reader.StartTime.ToUniversalTime().Ticks;OwnedPid=$reader.Id;OwnedExe=$reader.MainModule.FileName;Clock=[Diagnostics.Stopwatch]::StartNew();Directory=$temp;Nonce=('a'*48);Now=$now}
 $gate=Get-Usb500Gate @params
 if($gate.host_ready.capture_id -ne ('usb500-r7-'+('a'*48))){throw 'R7 capture identity failed'}
 $ports[6].Decoded.Status=0;SaveFrame
 $rejected=$false;try{Get-Usb500Gate @params|Out-Null}catch{$rejected=$true};if(-not $rejected){throw 'logical config alone passed physical GET status'}
 $ports[6].Decoded.Status=1;SaveFrame;$meta.DecoderSha256='0'*64
 [IO.File]::WriteAllText((Join-Path $temp 'metadata-private.json'),($meta|ConvertTo-Json))
 $rejected=$false;try{Get-Usb500Gate @params|Out-Null}catch{$rejected=$true};if(-not $rejected){throw 'different GET decoder accepted'}
 $result=@{passed=$true;cases=3;sequences=@('actual current process ownership and R7 capture identity','GET connection status required despite config1','frozen GET source required');coordinator_executed=$false;usb_access=$false;device_access=$false;frozen12_suite_rerun=$false;parent_sha256=(Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant();test_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()}
 [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'parent-migration-test-result.json'),(($result|ConvertTo-Json -Depth 8)+"`n"),[Text.UTF8Encoding]::new($false))
 $result|ConvertTo-Json -Depth 8
}finally{
 $reader.Dispose()
 $resolvedTemp=[IO.Path]::GetFullPath($temp)
 $intendedParent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar)
 if([IO.Path]::GetDirectoryName($resolvedTemp) -ne $intendedParent -or [IO.Path]::GetFileName($resolvedTemp) -notmatch '^usb500-r7-parent-[0-9a-f]{32}$'){throw 'Refuse cleanup outside the one test temp directory'}
 Remove-Item -LiteralPath $temp -Recurse -Force
}
