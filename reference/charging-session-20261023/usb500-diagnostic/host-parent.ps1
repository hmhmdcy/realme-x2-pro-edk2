param([Alias('-WindowConfirmed')][switch]$WindowConfirmed)
# Only this explicit coordinator can dispatch once. Source functions are also
# exercised offline; the main body is never invoked by those tests.
$ErrorActionPreference='Stop'

function Read-Usb500SharedText([string]$Path) {
    $stream=[IO.FileStream]::new($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try {
        if ($stream.Length -gt 16MB) { throw 'Unexpectedly large host capture' }
        $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $stream.Dispose() }
}

function Convert-Usb500CaptureUtc($Value) {
    # ConvertFrom-Json in newer pwsh adapts offset strings to local DateTime.
    if ($Value -is [DateTime] -and $Value.Kind -eq [DateTimeKind]::Unspecified) { throw 'Capture timestamp has no offset' }
    if ($Value -is [string] -and $Value -notmatch '(Z|[+-]\d\d:\d\d)$') { throw 'Capture timestamp has no offset' }
    return ([DateTimeOffset]$Value).ToUniversalTime()
}

function Get-Usb500Gate {
    param([Diagnostics.Process]$Reader,[long]$OwnedHandle,[long]$OwnedStartTicks,[int]$OwnedPid,
          [string]$OwnedExe,[Diagnostics.Stopwatch]$Clock,[string]$Directory,[string]$Nonce,
          [DateTimeOffset]$Now=[DateTimeOffset]::UtcNow)
    if ($Reader.HasExited -or $Reader.Id -ne $OwnedPid -or $OwnedHandle -eq 0 -or
        $Reader.Handle.ToInt64() -ne $OwnedHandle -or $Reader.StartTime.ToUniversalTime().Ticks -ne $OwnedStartTicks -or
        -not [string]::Equals([IO.Path]::GetFullPath($Reader.MainModule.FileName),[IO.Path]::GetFullPath($OwnedExe),[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Reader process handle/start/image no longer matches the owned process'
    }
    $remaining=[Math]::Floor(140-$Clock.Elapsed.TotalSeconds)
    if ($remaining -lt 110) { throw 'Insufficient conservative parent stopwatch time' }
    $meta=Read-Usb500SharedText (Join-Path $Directory 'metadata-private.json') | ConvertFrom-Json
    $ready=Read-Usb500SharedText (Join-Path $Directory 'ready.json') | ConvertFrom-Json
    if ($meta.ReadOnly -ne $true -or $meta.DurationSeconds -ne 140 -or $meta.PortCount -lt 1 -or $meta.PortCount -gt 15 -or
        $meta.DecoderSha256 -ne '9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716' -or
        $meta.CollectorSha256 -ne '31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5' -or
        $ready.Armed -ne $true -or $ready.DurationSeconds -ne 140) { throw 'Reader source/configuration/ready differs' }
    $text=Read-Usb500SharedText (Join-Path $Directory 'ports-private.jsonl')
    $lines=$text -split "`n"
    if (-not $text.EndsWith("`n")) {
        if ($lines.Count -le 1) { throw 'No newline-terminated complete sweep' }
        $lines=$lines[0..($lines.Count-2)]
    }
    $complete=@($lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($complete.Count -eq 0) { throw 'No complete sweep' }
    $frame=$complete[-1] | ConvertFrom-Json
    if ($frame.Armed -ne $true -or $frame.PartialSweep -ne $false -or $frame.Ports.Count -ne $meta.PortCount -or
        $frame.PinnedTargetPort -ne $ready.TargetPort -or $frame.EndMs-$frame.StartMs -gt 2000 -or $frame.EndMs -lt $frame.StartMs) { throw 'Incomplete/currently unarmed sweep' }
    $when=Convert-Usb500CaptureUtc $frame.Utc
    if (($Now-$when).TotalSeconds -lt 0 -or ($Now-$when).TotalSeconds -gt 3) { throw 'Last complete armed sweep is not fresh' }
    $ports=@($frame.Ports.Port | Sort-Object -Unique)
    if ($ports.Count -ne $meta.PortCount -or $ports[0] -ne 1 -or $ports[-1] -ne $meta.PortCount) { throw 'Not a complete unique port set' }
    foreach ($port in $frame.Ports) {
        $age=($Now-(Convert-Usb500CaptureUtc $port.Utc)).TotalSeconds
        if ($port.PSObject.Properties['Error'] -or $null -eq $port.Decoded -or $port.Decoded.ExpectedPort -ne $port.Port -or
            $port.Decoded.Port -ne $port.Port -or $age -lt 0 -or $age -gt 3) { throw 'A port is unparsed or stale' }
    }
    $targets=@($frame.Ports | Where-Object { $_.Decoded.Status -eq 1 -and $_.Decoded.DescriptorValid -eq $true -and
        $_.Decoded.Vendor -eq '0525' -and $_.Decoded.Product -eq 'a4a1' -and $_.Decoded.Configuration -eq 1 -and $_.Decoded.IsHub -eq $false })
    if ($targets.Count -ne 1 -or $targets[0].Port -ne $ready.TargetPort -or @($frame.TargetMatches).Count -ne 1 -or
        $frame.TargetMatches[0] -ne $ready.TargetPort) { throw 'NCM target identity/configuration is not unique' }
    return [ordered]@{
        owned_handle_checked=$true; host_trigger_utc=$Now.ToString('o')
        host_ready=[ordered]@{ armed=$true; target_port=[int]$ready.TargetPort; remaining_seconds_at_trigger=$remaining
            decoder_sha256=$meta.DecoderSha256; collector_sha256=$meta.CollectorSha256; host_worker_pid=$OwnedPid
            capture_id=('usb500-r6-'+$Nonce); ready_at_utc=$when.ToString('o') }
        reader_proof=[ordered]@{ pid=$OwnedPid; handle=$OwnedHandle; start_ticks=$OwnedStartTicks; exe=$OwnedExe; sweep=$frame.Sweep }
    }
}

function Write-Usb500NewJson([string]$Path,$Value) {
    $stream=[IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 12));$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true) }
    finally { $stream.Dispose() }
}

function Convert-Usb500WslPath([string]$Path) {
    $full=[IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^E:\\' -or $full.Contains('"')) { throw 'Only the fixed E: workspace paths are supported' }
    return '/mnt/e/'+$full.Substring(3).Replace('\','/')
}

function Start-Usb500Launcher([string]$Action,[string]$Nonce,[string]$Gate,[string]$Out,[string]$Source) {
    $arguments=@('-d','Ubuntu','-u','root','--','python3',('"'+(Convert-Usb500WslPath $Source)+'"'),$Action,'--nonce',$Nonce)
    if ($Action -eq 'launch') { $arguments+=@('--host-ready-file',('"'+(Convert-Usb500WslPath $Gate)+'"'),'--window-confirmed') }
    return Start-Process -FilePath (Get-Command wsl.exe).Source -ArgumentList $arguments -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Out ($Action+'-parent-stdout-private.json')) -RedirectStandardError (Join-Path $Out ($Action+'-parent-stderr-private.txt'))
}

if (-not $WindowConfirmed) { throw 'Explicit --WindowConfirmed and actual camera/Bluetooth handback are required' }
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'pwsh7 required for owned reader process-tree cleanup' }
$review=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'orchestration-test-result.json') -Raw | ConvertFrom-Json
if ($review.passed -ne $true) { throw 'Passing offline orchestration receipt required' }
foreach ($reviewName in @('host-parent.ps1','host-launcher.py','watch-one-hub.ps1','UsbHubReadOnly.cs')) {
    if ((Get-FileHash (Join-Path $PSScriptRoot $reviewName) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $review.tested_files.$reviewName) { throw 'Orchestration source differs from offline receipt' }
}
$nonce=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24)).ToLowerInvariant()
$out=Join-Path 'E:/edk2-samurai-out/charging-management-20261023' ('usb500-r6-'+$nonce)
New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
$hostOut=Join-Path $out 'host-reader'
$source=Join-Path $PSScriptRoot 'host-launcher.py'
$clock=[Diagnostics.Stopwatch]::StartNew()
$reader=$null;$launch=$null;$fetch=$null;$dispatched=$false;$failure=$null;$readerKilled=$false
Write-Usb500NewJson (Join-Path $out 'parent-start-private.json') @{nonce=$nonce;utc=[DateTimeOffset]::UtcNow.ToString('o');dispatch_count=0}
try {
    $exe=(Get-Command pwsh.exe).Source
    $reader=Start-Process -FilePath $exe -ArgumentList @('-NoProfile','-NonInteractive','-File',('"'+(Join-Path $PSScriptRoot 'watch-one-hub.ps1')+'"'),
        '-OutputDirectory',('"'+$hostOut+'"'),'-DurationSeconds','140','-IntervalMs','200') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $out 'reader-stdout-private.json') -RedirectStandardError (Join-Path $out 'reader-stderr-private.txt')
    $handle=$reader.Handle.ToInt64();$start=$reader.StartTime.ToUniversalTime().Ticks;$pidOwned=$reader.Id
    Write-Usb500NewJson (Join-Path $out 'reader-owned-private.json') @{pid=$pidOwned;handle=$handle;start_ticks=$start;exe=$exe;nonce=$nonce}
    $gate=$null;$lastGateError=$null
    while ($clock.Elapsed.TotalSeconds -lt 30 -and -not $reader.HasExited) {
        try { $gate=Get-Usb500Gate -Reader $reader -OwnedHandle $handle -OwnedStartTicks $start -OwnedPid $pidOwned -OwnedExe $exe -Clock $clock -Directory $hostOut -Nonce $nonce }
        catch { $lastGateError=$_.Exception.Message }
        if ($null -ne $gate) { break }
        Start-Sleep -Milliseconds 200
    }
    if ($null -eq $gate) { throw ('No current owned reader gate: '+$lastGateError) }
    $gateFile=Join-Path $out 'host-ready-private.json'
    Write-Usb500NewJson $gateFile $gate
    Write-Usb500NewJson (Join-Path $out 'parent-dispatch-once-private.json') @{nonce=$nonce;utc=[DateTimeOffset]::UtcNow.ToString('o');dispatch_count=1}
    $dispatched=$true  # any unknown launch outcome is fetch-only
    $launch=Start-Usb500Launcher 'launch' $nonce $gateFile $out $source
} catch { $failure=$_.Exception.ToString() }
finally {
    # Keep the reader independent of SSH loss; never terminate phone/SSH workers.
    if ($null -ne $reader) {
        while (-not $reader.WaitForExit(500)) {
            if ($clock.Elapsed.TotalSeconds -ge 160) { $reader.Kill($true);$readerKilled=$true;break }
        }
        $readerExited=$reader.WaitForExit(3000)
    } else { $readerExited=$false }
    if ($dispatched) {
        try {
            $fetch=Start-Usb500Launcher 'fetch' $nonce '' $out $source
            $fetch.WaitForExit(60000) | Out-Null  # read-only, same retained nonce; never relaunch
        } catch { $failure=($_.Exception.ToString()) }
    }
    $report=[ordered]@{nonce=$nonce;output=$out;dispatch_count=$(if($dispatched){1}else{0});reader_exited=$readerExited
        reader_watchdog_killed=$readerKilled;failure=$failure;launch_pid=$(if($launch){$launch.Id}else{$null})
        launch_exited=$(if($launch){$launch.HasExited}else{$null});fetch_pid=$(if($fetch){$fetch.Id}else{$null})
        fetch_exited=$(if($fetch){$fetch.HasExited}else{$null});phone_worker_killed=$false}
    Write-Usb500NewJson (Join-Path $out 'parent-result-private.json') $report
    $report | ConvertTo-Json
    foreach ($process in @($reader,$launch,$fetch)) { if ($null -ne $process) { $process.Dispose() } }
}
