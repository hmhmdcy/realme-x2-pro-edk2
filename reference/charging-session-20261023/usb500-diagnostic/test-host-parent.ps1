# Offline: execute only actual pure parent gate/file functions. The owned
# process is a hidden local sleep process, never a USB reader/WSL/SSH worker.
$ErrorActionPreference='Stop'
$parentPath=Join-Path $PSScriptRoot 'host-parent.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($parentPath,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Parent syntax failed' }
foreach ($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in @('Read-Usb500SharedText','Convert-Usb500CaptureUtc','Get-Usb500Gate','Write-Usb500NewJson','Convert-Usb500WslPath')},$true)) {
    Invoke-Expression $node.Extent.Text
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('usb500-parent-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$exe=(Get-Command pwsh.exe).Source
$reader=Start-Process -FilePath $exe -ArgumentList @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 30') -WindowStyle Hidden -PassThru
$cases=[Collections.Generic.List[string]]::new()
function Check([bool]$Value,[string]$Name) { if(-not $Value){throw $Name};$cases.Add($Name) }
function Reject([scriptblock]$Action,[string]$Name) {
    $bad=$false;try { &$Action | Out-Null }catch{$bad=$true};Check $bad $Name
}
try {
    $now=[DateTimeOffset]::UtcNow
    $meta=[ordered]@{ReadOnly=$true;DurationSeconds=140;PortCount=7
        DecoderSha256='9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716'
        CollectorSha256='31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5'}
    $ready=[ordered]@{Armed=$true;DurationSeconds=140;TargetPort=7}
    $ports=@(1..7 | ForEach-Object { [pscustomobject]@{Port=$_;Utc=$now.ToString('o');Decoded=[pscustomobject]@{
        Port=$_;ExpectedPort=$_;Status=$(if($_ -eq 1 -or $_ -eq 7){1}else{0});DescriptorValid=($_ -eq 1 -or $_ -eq 7)
        Vendor=$(if($_ -eq 7){'0525'}elseif($_ -eq 1){'05c6'}else{'0000'})
        Product=$(if($_ -eq 7){'a4a1'}elseif($_ -eq 1){'9501'}else{'0000'});Configuration=1;IsHub=$false}} })
    $frame=[ordered]@{Utc=$now.ToString('o');Armed=$true;PartialSweep=$false;StartMs=5000;EndMs=5010
        PinnedTargetPort=7;TargetMatches=@(7);Sweep=27;Ports=$ports}
    $metaPath=Join-Path $temp 'metadata-private.json';$readyPath=Join-Path $temp 'ready.json';$rowsPath=Join-Path $temp 'ports-private.jsonl'
    Write-Usb500NewJson $metaPath $meta;Write-Usb500NewJson $readyPath $ready
    function Rows { [IO.File]::WriteAllText($rowsPath,(($frame | ConvertTo-Json -Depth 8 -Compress)+"`n")) }
    Rows
    $clock=[Diagnostics.Stopwatch]::StartNew()
    $params=@{Reader=$reader;OwnedHandle=$reader.Handle.ToInt64();OwnedStartTicks=$reader.StartTime.ToUniversalTime().Ticks
        OwnedPid=$reader.Id;OwnedExe=$exe;Clock=$clock;Directory=$temp;Nonce=('a'*48);Now=$now}
    $gate=Get-Usb500Gate @params
    Check ($gate.owned_handle_checked -and $gate.host_ready.target_port -eq 7 -and $gate.host_ready.remaining_seconds_at_trigger -ge 110) 'actual-owned-process-handle-start-and-complete-gate'
    $frame.Utc=$now.AddSeconds(-4).ToString('o');Rows
    Reject {Get-Usb500Gate @params} 'last-complete-sweep-older-than-three-seconds-refused'
    $frame.Utc=$now.ToString('o');$frame.PartialSweep=$true;Rows
    Reject {Get-Usb500Gate @params} 'partial-armed-sweep-refused'
    $frame.PartialSweep=$false;$ports[6].Decoded.Configuration=0;Rows
    Reject {Get-Usb500Gate @params} 'target-must-be-config1-currently'
    $ports[6].Decoded.Configuration=1;Rows
    $wrong=$params.Clone();$wrong.OwnedStartTicks++
    Reject {Get-Usb500Gate @wrong} 'owned-process-start-fingerprint-mismatch-refused'
    $meta.DecoderSha256='0'*64;[IO.File]::WriteAllText($metaPath,($meta|ConvertTo-Json))
    Reject {Get-Usb500Gate @params} 'different-decoder-source-refused'
    $meta.DecoderSha256='9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716';[IO.File]::WriteAllText($metaPath,($meta|ConvertTo-Json));Rows
    [IO.File]::AppendAllText($rowsPath,'{"incomplete":')
    Check ((Get-Usb500Gate @params).host_ready.target_port -eq 7) 'only-newline-complete-last-sweep-used'
    [IO.File]::WriteAllText($rowsPath,'{"incomplete":')
    Reject {Get-Usb500Gate @params} 'no-complete-line-refused'
    Reject {Write-Usb500NewJson $readyPath $ready} 'durable-create-new-marker-never-overwrites'
    Check ((Convert-Usb500WslPath 'E:/RealmeX2Pro edk2/a.json') -eq '/mnt/e/RealmeX2Pro edk2/a.json') 'fixed-WSL-path-preserves-spaces'
    $reader.Kill($true);$reader.WaitForExit(3000) | Out-Null
    Reject {Get-Usb500Gate @params} 'exited-owned-reader-refused'
    # Verify the exact double-dash opt-in binding on a harmless script that
    # contains only the real ParamBlock and emits its resulting boolean.
    $probe=Join-Path $temp 'flag-only.ps1'
    [IO.File]::WriteAllText($probe,$ast.ParamBlock.Extent.Text+"`n[bool]`$WindowConfirmed")
    $probeOut=Join-Path $temp 'flag.txt'
    $probeProcess=Start-Process -FilePath $exe -ArgumentList @('-NoProfile','-NonInteractive','-File',('"'+$probe+'"'),'--WindowConfirmed') -WindowStyle Hidden -PassThru -RedirectStandardOutput $probeOut
    try { $probeProcess.WaitForExit(5000) | Out-Null;Check ((Get-Content -Raw $probeOut).Trim() -eq 'True') 'explicit-double-dash-WindowConfirmed-binding' }
    finally {if(-not $probeProcess.HasExited){$probeProcess.Kill($true)};$probeProcess.Dispose()}
    [ordered]@{passed=$true;cases=$cases.Count;case_names=$cases.ToArray()
        tested_parent_sha256=(Get-FileHash -LiteralPath $parentPath -Algorithm SHA256).Hash.ToLowerInvariant()
        test_script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
        usb_reader_started=$false;network_accessed=$false;device_accessed=$false} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'parent-gate-test-result.json') -Encoding utf8
    [pscustomobject]@{passed=$true;cases=$cases.Count} | ConvertTo-Json
} finally {
    if(-not $reader.HasExited){$reader.Kill($true)};$reader.Dispose()
    # Keep the uniquely named temporary evidence; no recursive removal.
}
