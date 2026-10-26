param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateRange(30,180)][int]$DurationSeconds = 100,
    [ValidateRange(100,1000)][int]$IntervalMs = 200,
    [ValidateRange(2,15)][int]$BaselineSeconds = 5,
    [ValidateRange(20,500)][int]$QueryTimeoutMs = 100
)
# Read-only host capture. Invocation requires the actual coordinated window.
# No reset/cycle/configuration/descriptor write/driver install/PnP restart.
$ErrorActionPreference = 'Stop'
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) { throw 'Use an explicit absolute new private output directory' }
$diagnosticOut = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $diagnosticOut -ErrorAction Stop | Out-Null
if ('SamuraiUsb500.Decode' -as [type]) { throw 'Start a fresh PowerShell process; never reuse a previously loaded decoder' }
Add-Type -Path (Join-Path $PSScriptRoot 'UsbHubReadOnly.cs')
$diagnosticClock = [System.Diagnostics.Stopwatch]::StartNew()
$diagnosticSession = $null
$diagnosticLog = $null
$diagnosticArmed = $false
$diagnosticTargetPort = $null
$diagnosticCandidatePort = $null
$diagnosticStable = 0
$diagnosticSweeps = 0
$diagnosticQueries = 0
$diagnosticQueryErrors = 0
$diagnosticTargetPower = $false
$diagnosticTargetMoved = $false
$diagnosticCounts = @{}
$diagnosticStop = 'not_started'
$diagnosticFailure = $null
$diagnosticMeta = $null

function Get-Usb500NcmRootHub {
    # Sole exact present composite NCM; exclude MI children and old EUD hub.
    $ncm = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_0525&PID_A4A1\\[^\\]+$' })
    if ($ncm.Count -ne 1 -or $ncm[0].InstanceId -notmatch '^USB\\VID_0525&PID_A4A1\\62BC28A1$') {
        throw 'Expected the sole exact original NCM composite identity'
    }
    $parents = @(Get-PnpDeviceProperty -InstanceId $ncm[0].InstanceId -KeyName 'DEVPKEY_Device_Parent')
    if ($parents.Count -ne 1 -or $parents[0].Type -ne 'String' -or
        $parents[0].Data -notmatch '^USB\\ROOT_HUB(?:20|30)?\\[^\\]+$') {
        throw 'NCM must currently be a direct child of a root hub; no EUD/other hub fallback'
    }
    $hubs = @(Get-PnpDevice -PresentOnly -InstanceId $parents[0].Data)
    if ($hubs.Count -ne 1 -or $hubs[0].InstanceId -ne $parents[0].Data) { throw 'Current parent root hub is not unique/present' }
    $text = (& pnputil /enum-devices /instanceid $hubs[0].InstanceId /interfaces | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Read-only root-hub interface enumeration failed' }
    $expectedInterface = '\\?\' + $hubs[0].InstanceId.Replace('\','#') + '#{f18a0e88-c30c-11d0-8815-00a0c906bed8}'
    $pattern = [regex]::Escape($expectedInterface)
    $matches = [regex]::Matches($text, $pattern, 'IgnoreCase')
    if ($matches.Count -ne 1) { throw 'Expected one interface of that exact present root hub' }
    return [ordered]@{ NcmInstance=$ncm[0].InstanceId; HubInstance=$hubs[0].InstanceId; Interface=$matches[0].Value }
}

try {
    $diagnosticTopology = Get-Usb500NcmRootHub
    $diagnosticPath = $diagnosticTopology.Interface
    $diagnosticSession = [SamuraiUsb500.HubSession]::new($diagnosticPath)
    $diagnosticNodeRaw = $diagnosticSession.Query([SamuraiUsb500.Decode]::GetNode, 0, $QueryTimeoutMs)
    $diagnosticNode = [SamuraiUsb500.Decode]::Hub($diagnosticNodeRaw)
    $diagnosticMeta = [ordered]@{
        ReadOnly=$true; WindowsSdk='10.0.26100.0'; Interface=$diagnosticPath
        HubInstance=$diagnosticTopology.HubInstance; NcmInstance=$diagnosticTopology.NcmInstance
        DirectRootHub=$true; PortCount=$diagnosticNode.Ports
        HubIsBusPowered=$diagnosticNode.BusPowered; HubControllerCurrentMa=$diagnosticNode.ControllerCurrentMa
        NodeBase64=[Convert]::ToBase64String($diagnosticNodeRaw)
        StartUtc=[DateTimeOffset]::UtcNow.ToString('o'); StopwatchFrequency=[System.Diagnostics.Stopwatch]::Frequency
        DurationSeconds=$DurationSeconds; IntervalMs=$IntervalMs; QueryTimeoutMs=$QueryTimeoutMs
        BaselineSeconds=$BaselineSeconds; Identity='0525:a4a1, connected, configuration 1, valid descriptor, non-hub'
        DecoderSha256=(Get-FileHash (Join-Path $PSScriptRoot 'UsbHubReadOnly.cs') -Algorithm SHA256).Hash.ToLowerInvariant()
        CollectorSha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $diagnosticMeta | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $diagnosticOut 'metadata-private.json') -Encoding utf8
    $diagnosticLog = [System.IO.StreamWriter]::new((Join-Path $diagnosticOut 'ports-private.jsonl'), $false, [System.Text.UTF8Encoding]::new($false))
    $diagnosticLog.AutoFlush = $true
    $diagnosticStop = 'deadline'
    $diagnosticClock.Restart()
    while ($diagnosticClock.Elapsed.TotalSeconds -lt $DurationSeconds) {
        $diagnosticSweepStart = $diagnosticClock.Elapsed.TotalMilliseconds
        $diagnosticRows = @()
        $diagnosticTargets = @()
        for ($diagnosticPort=1; $diagnosticPort -le $diagnosticNode.Ports; $diagnosticPort++) {
            if ($diagnosticClock.Elapsed.TotalSeconds -ge $DurationSeconds) { break }
            $diagnosticOne = [ordered]@{ Port=$diagnosticPort; QueryStartMs=$diagnosticClock.Elapsed.TotalMilliseconds; Utc=[DateTimeOffset]::UtcNow.ToString('o') }
            try {
                $diagnosticQueries++
                $diagnosticRaw = $diagnosticSession.Query([SamuraiUsb500.Decode]::GetConnectionEx, [uint32]$diagnosticPort, $QueryTimeoutMs)
                $diagnosticOne['RawBase64'] = [Convert]::ToBase64String($diagnosticRaw)
                $diagnosticDecoded = [SamuraiUsb500.Decode]::Port($diagnosticRaw, [uint32]$diagnosticPort)
                $diagnosticOne['Decoded'] = $diagnosticDecoded
                $diagnosticCountKey = '{0}:{1}' -f $diagnosticPort,$diagnosticDecoded.StatusName
                if (-not $diagnosticCounts.ContainsKey($diagnosticCountKey)) { $diagnosticCounts[$diagnosticCountKey]=0 }
                $diagnosticCounts[$diagnosticCountKey]++
                if ([SamuraiUsb500.Decode]::Target($diagnosticDecoded)) { $diagnosticTargets += $diagnosticPort }
                if ($diagnosticArmed -and $diagnosticPort -eq $diagnosticTargetPort -and $diagnosticDecoded.Status -eq 5) {
                    $diagnosticTargetPower = $true
                }
            } catch {
                $diagnosticQueryErrors++
                $diagnosticOne['Error'] = $_.Exception.ToString()
                # Record the error/partial sweep before aborting unresolved IO.
                if ($_.Exception.ToString().Contains('UnresolvedReadException')) {
                    $diagnosticStop = 'unresolved_read_cancellation'
                }
            } finally {
                $diagnosticOne['QueryEndMs'] = $diagnosticClock.Elapsed.TotalMilliseconds
                $diagnosticRows += [pscustomobject]$diagnosticOne
            }
            if ($diagnosticStop -eq 'unresolved_read_cancellation') { break }
        }
        $diagnosticSweeps++
        $diagnosticFrame = [ordered]@{
            Sweep=$diagnosticSweeps; Utc=[DateTimeOffset]::UtcNow.ToString('o')
            StartMs=$diagnosticSweepStart; EndMs=$diagnosticClock.Elapsed.TotalMilliseconds
            Armed=$diagnosticArmed; PinnedTargetPort=$diagnosticTargetPort
            TargetMatches=$diagnosticTargets; PartialSweep=($diagnosticRows.Count -ne $diagnosticNode.Ports)
            Ports=$diagnosticRows
        }
        $diagnosticLog.WriteLine(($diagnosticFrame | ConvertTo-Json -Depth 9 -Compress))
        if ($diagnosticStop -eq 'unresolved_read_cancellation') { break }
        if (-not $diagnosticArmed) {
            $diagnosticAllParsed = @($diagnosticRows | Where-Object { $_.PSObject.Properties.Name -contains 'Error' }).Count -eq 0
            if ($diagnosticTargets.Count -eq 1 -and $diagnosticRows.Count -eq $diagnosticNode.Ports -and $diagnosticAllParsed) {
                if ($diagnosticCandidatePort -eq $diagnosticTargets[0]) { $diagnosticStable++ }
                else { $diagnosticCandidatePort=$diagnosticTargets[0]; $diagnosticStable=1 }
            } else { $diagnosticStable=0 }
            if ($diagnosticClock.Elapsed.TotalSeconds -ge $BaselineSeconds) {
                if ($diagnosticTargets.Count -ne 1 -or $diagnosticStable -lt 3) {
                    $diagnosticStop='baseline_target_absent_ambiguous_or_unstable'
                    break
                }
                $diagnosticTargetPort=$diagnosticCandidatePort
                $diagnosticArmed=$true
                [ordered]@{ Armed=$true; Utc=[DateTimeOffset]::UtcNow.ToString('o'); ElapsedMs=$diagnosticClock.Elapsed.TotalMilliseconds
                    TargetPort=$diagnosticTargetPort; StableSweeps=$diagnosticStable; DurationSeconds=$DurationSeconds } |
                    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $diagnosticOut 'ready.json') -Encoding utf8
            }
        } elseif (@($diagnosticTargets | Where-Object { $_ -ne $diagnosticTargetPort }).Count -gt 0) {
            $diagnosticTargetMoved=$true
        }
        $diagnosticDelay=[int][Math]::Max(0, [Math]::Min($IntervalMs-($diagnosticClock.Elapsed.TotalMilliseconds-$diagnosticSweepStart), $DurationSeconds*1000-$diagnosticClock.Elapsed.TotalMilliseconds))
        if ($diagnosticDelay -gt 0) { Start-Sleep -Milliseconds $diagnosticDelay }
    }
} catch {
    $diagnosticFailure=$_.Exception.ToString()
    $diagnosticStop='collector_error'
} finally {
    if ($null -ne $diagnosticLog) { $diagnosticLog.Dispose() }
    if ($null -ne $diagnosticSession) { $diagnosticSession.Dispose() }
    $diagnosticSummary=[ordered]@{
        ReadOnly=$true; TrialExecutedByCollector=$false; Terminal=$true
        Armed=$diagnosticArmed; PinnedTargetPort=$diagnosticTargetPort; StopReason=$diagnosticStop
        EndUtc=[DateTimeOffset]::UtcNow.ToString('o'); ElapsedSeconds=$diagnosticClock.Elapsed.TotalSeconds
        Sweeps=$diagnosticSweeps; Queries=$diagnosticQueries; QueryErrors=$diagnosticQueryErrors
        ExplicitPowerStatusOnPinnedPortObserved=$diagnosticTargetPower; TargetSeenOnDifferentPort=$diagnosticTargetMoved
        StatusCounts=$diagnosticCounts; Failure=$diagnosticFailure
        CausalConclusion='Requires phase/time correlation with new device transaction; generic failure/absence does not prove power rejection'
    }
    $diagnosticSummary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $diagnosticOut 'summary.json') -Encoding utf8
    $diagnosticSummary | ConvertTo-Json -Depth 8
}
if ($null -ne $diagnosticFailure -or -not $diagnosticArmed -or $diagnosticStop -ne 'deadline') { exit 1 }
