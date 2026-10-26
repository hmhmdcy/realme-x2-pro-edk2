param([switch]$ResumeUnstarted, [switch]$ResumeAfterCandidates)
$ErrorActionPreference = 'Stop'
$buildRoot = [IO.Path]::GetFullPath('E:\edk2-samurai-out')
$cleanupRoot = [IO.Path]::GetFullPath((Join-Path $buildRoot 'cleanup145'))
$ledgerPath = Join-Path $cleanupRoot 'cleanup-ledger-private.json'
$volumeRoot = Join-Path $cleanupRoot 'volumes'
$publicReport = 'E:\RealmeX2Pro edk2\reference\kernel145\cleanup-validation.json'
$resumeCandidatesDone = $false
if ($ResumeUnstarted -and $ResumeAfterCandidates) { throw 'Choose only the inspected continuation state' }
if (Test-Path -LiteralPath $ledgerPath) {
    $previous = Get-Content -Raw -LiteralPath $ledgerPath | ConvertFrom-Json
    if ($ResumeAfterCandidates) {
        if ($previous.complete -or @($previous.removed).Count -ne 98 -or
            @($previous.archived_volumes).Count -ne 0 -or
            @($previous.removed | Where-Object { -not $_.removed -or $_.kind -ne 'obsolete_generated_candidate' }).Count -ne 0 -or
            $previous.iso_duplicate_chunks_verified) { throw 'Candidate-only continuation state mismatch' }
        $snapshot = [IO.Path]::GetFullPath((Join-Path $cleanupRoot 'cleanup-ledger-after-candidates-private.json'))
        if (-not $snapshot.StartsWith($buildRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
            (Test-Path -LiteralPath $snapshot)) { throw 'Unexpected continuation snapshot destination' }
        Copy-Item -LiteralPath $ledgerPath -Destination $snapshot
        $resumeCandidatesDone = $true
    } else {
        if (-not $ResumeUnstarted -or $previous.complete -or @($previous.removed).Count -ne 0 -or @($previous.archived_volumes).Count -ne 0) {
            throw 'Only an inspected, entirely unstarted cleanup may be retried'
        }
        $rejectedLedger = [IO.Path]::GetFullPath((Join-Path $cleanupRoot 'cleanup-ledger-preflight-rejected-private.json'))
        if (-not $rejectedLedger.StartsWith($buildRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
            (Test-Path -LiteralPath $rejectedLedger)) { throw 'Unexpected retry ledger destination' }
        Move-Item -LiteralPath $ledgerPath -Destination $rejectedLedger
    }
} elseif ($ResumeUnstarted -or $ResumeAfterCandidates) {
    throw 'Continuation requires an existing ledger'
}
New-Item -ItemType Directory -Path $volumeRoot -Force | Out-Null
$freeBefore = (Get-PSDrive -Name E).Free
$inventory = Get-Content -Raw -LiteralPath (Join-Path $buildRoot 'kernel145\old-build-inventory-private.json') | ConvertFrom-Json
$preserved = @(
    @('kernel132\boot-partition-k132-charger.img', '501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6'),
    @('kernel132\modules-k132-private.tar.gz', '92e03906e3f437880590417070640bb0e81fada4638ab2a6dcaf8f57bbae923c'),
    @('kernel132\samurai-rootfs-f2fs-k132-device-fixed.simg', '290e7af5fdda219a558032f4f75dfec6979a32e66693f117964361a4fd903ccb'),
    @('kernel140\Image-k140-dma-diagnostic-private', '2b244772eb7e15ce587722cd3fed37f775a05d4562a4ac2e6b80701aeb04dc45'),
    @('kernel140\logdump-k140-dma-diagnostic.img', '0ac9d6678ba4218a049fca47090c4fdd290d03d6a1fd72a6d9f04f046b21d925'),
    @('kernel145\Image-k145-dsi-observation-private', 'f38c7bf0da64ea39c97233ee981ca2d99df481fb5c1efe94ee9de3863f061163')
)
function Assert-PrivatePath([string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($buildRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Cleanup path escaped private build output' }
    $item = Get-Item -LiteralPath $full
    if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) { throw 'Expected a regular build artifact' }
    return $item
}
foreach ($row in $preserved) {
    $item = Assert-PrivatePath (Join-Path $buildRoot $row[0])
    if ((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row[1]) { throw 'Required current or rollback artifact mismatch' }
}
& wsl -d Ubuntu -u root -- python3 -c 'from pathlib import Path; import subprocess; r=Path("/home/cy122/pmos-samurai-kernel136/kernel"); assert subprocess.check_output(["losetup","-l","-n","-O","BACK-FILE"],text=True).strip()==""; names=subprocess.check_output(["ps","-eo","comm="],text=True).split(); assert not any(n in ["make","cc1","cc1plus","clang","ld","aarch64-linux-gnu-ld","mcopy","e2fsck"] for n in names); import hashlib; assert hashlib.sha256((r/"arch/arm64/boot/Image").read_bytes()).hexdigest()=="f38c7bf0da64ea39c97233ee981ca2d99df481fb5c1efe94ee9de3863f061163"; print("CLEANUP_PREFLIGHT_NO_ACTIVE_BUILDS_OR_ATTACHED_BUILD_VOLUMES")'
if ($LASTEXITCODE -ne 0) { throw 'Active build or volume preflight failed' }
if ($resumeCandidatesDone) {
    $ledger = Get-Content -Raw -LiteralPath $ledgerPath | ConvertFrom-Json -AsHashtable
    $freeBefore = $ledger.free_bytes_before
    $ledger['continued_after_candidates_utc'] = [DateTime]::UtcNow.ToString('o')
} else {
    $ledger = [ordered]@{stage=145;user_requested_cleanup=$true;started_utc=[DateTime]::UtcNow.ToString('o');free_bytes_before=$freeBefore;removed=@();archived_volumes=@();protected_sha256_before_verified=$true;complete=$false;phone_modified=$false}
}
function Save-Ledger { $ledger | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $ledgerPath -Encoding utf8 }
Save-Ledger
$selected = @($inventory | Where-Object {
    ($_.Stage -match '^kernel(\d+)$' -and [int]$Matches[1] -lt 145 -and [int]$Matches[1] -notin 132,140 -and
     $_.Name -match '^(Image-k\d+|boot-partition-k\d+|logdump-k\d+|modules-k\d+|samurai-rootfs-f2fs.*\.simg$)' -and
     $_.Name -notmatch 'k(132|140|145)(\D|$)') -or
    ($_.Stage -eq 'rootfs01' -and $_.Name -eq 'samurai-rootfs-f2fs.simg')
})
if ($resumeCandidatesDone) {
    if ((Compare-Object @($selected.Path | Sort-Object) @($ledger.removed.path | Sort-Object))) { throw 'Removed candidate paths differ from inventory selection' }
    foreach ($row in $ledger.removed) {
        $full = [IO.Path]::GetFullPath($row.path)
        if (-not $full.StartsWith($buildRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $full)) { throw 'Candidate removal state changed' }
    }
    Write-Output 'CLEANUP_CONFIRMED_98_ALREADY_REMOVED_CANDIDATES_SKIPPED'
}
foreach ($row in $(if ($resumeCandidatesDone) { @() } else { $selected })) {
    $item = Assert-PrivatePath $row.Path
    if ($item.Length -ne $row.Bytes -or $item.LastWriteTimeUtc.Ticks -ne ([DateTime]$row.ModifiedUtc).ToUniversalTime().Ticks) { throw 'Old artifact changed since inventory' }
    $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $entry = [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=$hash;kind='obsolete_generated_candidate';removed=$false}
    $ledger.removed += $entry
    Save-Ledger
    Remove-Item -LiteralPath $item.FullName
    $entry.removed = $true
    Save-Ledger
    if ($ledger.removed.Count % 20 -eq 0) { Write-Output ('CLEANUP_OBSOLETE_CANDIDATES_REMOVED=' + $ledger.removed.Count) }
}
Write-Output ('CLEANUP_OBSOLETE_CANDIDATES_COMPLETE=' + $selected.Count)

# These eight files are retained download chunks of the already assembled ISO.
$isoPath = Join-Path $buildRoot 'rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$iso = Assert-PrivatePath $isoPath
if ($iso.Length -ne 20002537472) { throw 'Unexpected retained tool ISO' }
$isoHash = (Get-FileHash -LiteralPath $isoPath -Algorithm SHA256).Hash.ToLowerInvariant()
$digest = [Security.Cryptography.SHA256]::Create()
$buffer = New-Object byte[] (4MB)
$chunkBytes = 0L
$chunks = @()
for ($index=0; $index -lt 8; $index++) {
    $path = Join-Path $buildRoot ('rx61\ewdk-download\part-{0:00}.bin' -f $index)
    $item = Assert-PrivatePath $path
    $chunks += $item.FullName
    $stream = [IO.File]::Open($item.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        while (($count=$stream.Read($buffer,0,$buffer.Length)) -gt 0) { $null=$digest.TransformBlock($buffer,0,$count,$buffer,0); $chunkBytes += $count }
    } finally { $stream.Dispose() }
}
$null=$digest.TransformFinalBlock([byte[]]@(),0,0)
$chunksHash = [BitConverter]::ToString($digest.Hash).Replace('-','').ToLowerInvariant()
$digest.Dispose()
if ($chunkBytes -ne $iso.Length -or $chunksHash -ne $isoHash) { throw 'Chunk concatenation differs from retained ISO; chunks preserved' }
$ledger['iso_duplicate_chunks_verified'] = $true
$ledger['retained_iso_sha256'] = $isoHash
Save-Ledger
foreach ($path in $chunks) {
    $item = Assert-PrivatePath $path
    $entry = [ordered]@{path=$item.FullName;bytes=$item.Length;kind='verified_duplicate_iso_download_chunk';removed=$false}
    $ledger.removed += $entry
    Save-Ledger
    Remove-Item -LiteralPath $item.FullName
    $entry.removed = $true
    Save-Ledger
}
Write-Output 'CLEANUP_DUPLICATE_ISO_CHUNKS_REMOVED_20002537472_BYTES_ISO_RETAINED'

$specs = @(
    @('kernel134','build-volume.ext4',8589934592L),
    @('kernel118','build-volume.ext4',21474836480L),
    @('kernel122','rootfs-build-volume.ext4',25769803776L),
    @('kernel126','build-volume.ext4',25769803776L),
    @('kernel129','rootfs-build-volume.ext4',17179869184L)
)
foreach ($spec in $specs) {
    $source = Join-Path $buildRoot ($spec[0] + '\' + $spec[1])
    $archive = Join-Path $volumeRoot ($spec[0] + '-' + $spec[1] + '.zst')
    $item = Assert-PrivatePath $source
    if ($item.Length -ne $spec[2] -or (Test-Path -LiteralPath $archive)) { throw 'Volume identity or archive state mismatch' }
    if ((Get-PSDrive -Name E).Free -lt ($item.Length + 100MB)) { throw 'Insufficient worst-case archive capacity; volume preserved' }
    $linuxSource = '/mnt/e/' + $source.Substring(3).Replace('\','/')
    $linuxArchive = '/mnt/e/' + $archive.Substring(3).Replace('\','/')
    $attached = & wsl -d Ubuntu -u root -- losetup -j $linuxSource
    if ($LASTEXITCODE -ne 0 -or $attached) { throw 'Volume became attached; preserved' }
    Write-Output ('CLEANUP_ARCHIVING_INACTIVE_VOLUME=' + $spec[0])
    $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    $entry = [ordered]@{source=$source;archive=$archive;bytes=$item.Length;sha256=$hash;verified=$false;source_removed=$false}
    $ledger.archived_volumes += $entry
    Save-Ledger
    & wsl -d Ubuntu -u root -- zstd -q -T2 -3 --check -o $linuxArchive $linuxSource
    if ($LASTEXITCODE -ne 0) { throw 'Archive creation failed; original volume preserved' }
    $verification = & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel145/verify-zstd-archive.py' $linuxArchive $hash $item.Length
    if ($LASTEXITCODE -ne 0) { throw 'Archive verification failed; original volume preserved' }
    $verified = $verification | ConvertFrom-Json
    if (-not $verified.verified -or $verified.sha256 -ne $hash -or $verified.decompressed_bytes -ne $item.Length) { throw 'Archive verification result mismatch' }
    $current = Assert-PrivatePath $source
    if ($current.Length -ne $item.Length -or $current.LastWriteTimeUtc -ne $item.LastWriteTimeUtc) { throw 'Source changed during archival; preserved' }
    $attached = & wsl -d Ubuntu -u root -- losetup -j $linuxSource
    if ($LASTEXITCODE -ne 0 -or $attached) { throw 'Source attached during archival; preserved' }
    $entry.verified = $true
    $entry['archive_bytes'] = (Get-Item -LiteralPath $archive).Length
    Save-Ledger
    Remove-Item -LiteralPath $source
    $entry.source_removed = $true
    Save-Ledger
    Write-Output ('CLEANUP_ARCHIVE_VERIFIED_AND_INACTIVE_VOLUME_REMOVED=' + $spec[0])
}
foreach ($row in $preserved) {
    $item = Assert-PrivatePath (Join-Path $buildRoot $row[0])
    if ((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row[1]) { throw 'Protected artifact changed during cleanup' }
}
if ((Get-FileHash -LiteralPath $isoPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $isoHash) { throw 'Retained ISO changed' }
$freeAfter = (Get-PSDrive -Name E).Free
$ledger['protected_sha256_after_verified'] = $true
$ledger['free_bytes_after'] = $freeAfter
$ledger['free_bytes_increased'] = $freeAfter - $freeBefore
$ledger.complete = $true
$ledger['finished_utc'] = [DateTime]::UtcNow.ToString('o')
Save-Ledger
$summary = [ordered]@{stage=145;user_requested_cleanup=$true;removed_candidate_files=$selected.Count;duplicate_iso_chunks_removed=8;iso_preserved_and_hash_verified=$true;inactive_build_volumes_compressed_and_verified=5;old_volumes_fully_recoverable=$true;protected132_140_145_artifacts_sha256_before_after_verified=$true;private_logs_source_patches_factory_backups_preserved=$true;phone_modified=$false;free_bytes_before=$freeBefore;free_bytes_after=$freeAfter;free_bytes_increased=$freeAfter-$freeBefore;complete=$true;goal_complete=$false}
$summary | ConvertTo-Json | Set-Content -LiteralPath $publicReport -Encoding utf8
Write-Output ('CLEANUP_COMPLETE_FREE_BYTES_INCREASED=' + ($freeAfter-$freeBefore) + ' E_FREE_BYTES=' + $freeAfter)
