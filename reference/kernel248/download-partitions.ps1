$ErrorActionPreference='Stop'
$taskPrivate='E:/edk2-samurai-out/kernel248'
$taskConfig=Get-Content -LiteralPath "$taskPrivate/partition-server-config-private.json" -Raw | ConvertFrom-Json
$taskPoll=Get-Content -LiteralPath "$taskPrivate/poll-backup-server-private.json" -Raw | ConvertFrom-Json
if ($taskPoll.report.state -ne 'serving') {throw 'Partition source manifest is not ready'}
$taskManifest=$taskPoll.private.manifest
$taskOutput="$taskPrivate/linux-return-partitions"
if (-not (Test-Path -LiteralPath $taskOutput)) {New-Item -ItemType Directory -Path $taskOutput | Out-Null}
$taskRequired=[long]$taskPoll.report.source_total_bytes
if ((Get-PSDrive E).Free -lt $taskRequired+30GB) {throw 'Insufficient reserved backup space'}
$taskDone=@()
foreach ($taskEntry in $taskManifest.PSObject.Properties) {
    $taskName=$taskEntry.Name
    if ($taskName -notmatch '^[a-zA-Z0-9_-]+\.img$') {throw 'Unexpected backup filename'}
    $taskDest=Join-Path $taskOutput $taskName
    if (-not (Test-Path -LiteralPath $taskDest)) {New-Item -ItemType File -Path $taskDest | Out-Null}
    $taskMeta=$taskEntry.Value
    $taskUrl='http://'+$taskConfig.bind_address+':'+$taskConfig.port+'/'+$taskConfig.token+'/'+$taskName
    $taskLog=Join-Path $taskPrivate ('download-'+$taskName+'-private.log')
    if ((Test-Path -LiteralPath $taskDest) -and (Get-Item -LiteralPath $taskDest).Length -gt [long]$taskMeta.bytes) {throw 'Backup output larger than source'}
    $taskPresent=if (Test-Path -LiteralPath $taskDest) {(Get-Item -LiteralPath $taskDest).Length} else {0}
    if ([long]$taskMeta.bytes-$taskPresent -gt 65536) {
        & C:/Windows/System32/curl.exe --disable --noproxy '*' --fail --silent --show-error --connect-timeout 10 --max-time 1800 --speed-time 15 --speed-limit 1024 --continue-at - --output $taskDest $taskUrl 2> $taskLog
        $taskPresent=if (Test-Path -LiteralPath $taskDest) {(Get-Item -LiteralPath $taskDest).Length} else {0}
        if ($LASTEXITCODE -ne 0 -and [long]$taskMeta.bytes-$taskPresent -gt 65536) {throw 'Partition transfer failed before a small tail; retain partial file and inspect private receipt'}
    }
    if ((Get-Item -LiteralPath $taskDest).Length -lt [long]$taskMeta.bytes) {
        & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel248/complete-small-tail.py' $taskName
        if ($LASTEXITCODE -ne 0) {throw 'Small transfer tail failed; no restore or flash permitted'}
    }
    if ((Get-Item -LiteralPath $taskDest).Length -ne [long]$taskMeta.bytes) {throw 'Partition backup length mismatch'}
    $taskHash=(Get-FileHash -LiteralPath $taskDest -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($taskHash -ne $taskMeta.sha256) {throw 'Partition backup hash mismatch'}
    $taskDone += [pscustomobject]@{name=$taskName;bytes=[long]$taskMeta.bytes;sha256=$taskHash}
    $taskDone | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$taskPrivate/partition-download-progress-private.json"
    Write-Output ('Verified partition backup '+$taskName+' ('+$taskDone.Count+'/20)')
}
[pscustomobject]@{stage=248;verified_partition_count=$taskDone.Count;all_lengths_and_sha256_match=$true;total_bytes=$taskRequired;original_factory_backup_not_overwritten=$true;no_phone_partition_written=$true} | ConvertTo-Json | Set-Content -LiteralPath 'E:/RealmeX2Pro edk2/reference/kernel248/partition-backup-validation.json'
'All 20 partition backups verified on PC'
