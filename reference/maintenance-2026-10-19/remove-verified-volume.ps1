$ErrorActionPreference='Stop'
$buildRoot=[IO.Path]::GetFullPath('E:\edk2-samurai-out')
$sourcePath=[IO.Path]::GetFullPath((Join-Path $buildRoot 'kernel118\build-volume.ext4'))
$archivePath=[IO.Path]::GetFullPath((Join-Path $buildRoot 'cleanup20261019\kernel118-current-build-volume.ext4.zst'))
$receiptPath=Join-Path $buildRoot 'cleanup20261019\volume118-verification-private.json'
foreach($p in @($sourcePath,$archivePath)) {
    if(-not $p.StartsWith($buildRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Path escaped explicit build root'}
    $item=Get-Item -LiteralPath $p
    if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Regular file required'}
}
$record=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json -AsHashtable
if(-not $record.verified -or $record.original_removed -or $record.decompressed_bytes -ne 21474836480L -or $record.sha256 -ne 'f4a8328f0a5b2fe32c74695c70846ef4b7a176a98a23cf070c34a1ea4cc5bd96'){throw 'Full archive verification required'}
$source=Get-Item -LiteralPath $sourcePath
$archive=Get-Item -LiteralPath $archivePath
# zstd preserves mtime to whole seconds. Pin the inspected original's complete
# timestamp as well as comparing the archive's deliberately truncated value.
if($source.Length -ne $record.decompressed_bytes -or $archive.Length -ne $record.archive_bytes -or $source.LastWriteTimeUtc.ToString('o') -ne '2026-10-13T02:34:17.5399899Z' -or ([DateTimeOffset]$source.LastWriteTimeUtc).ToUnixTimeSeconds() -ne ([DateTimeOffset]$archive.LastWriteTimeUtc).ToUnixTimeSeconds()){throw 'Artifact changed since verification'}
$attached=& wsl.exe -d Ubuntu -u root -- losetup -j /mnt/e/edk2-samurai-out/kernel118/build-volume.ext4
if($LASTEXITCODE -ne 0 -or $attached){throw 'Original build image still attached'}
$record.free_bytes_before=(Get-PSDrive E).Free
$record.original_mtime_utc=$source.LastWriteTimeUtc.ToString('o')
Remove-Item -LiteralPath $sourcePath
$record.original_removed=$true
$record.free_bytes_after=(Get-PSDrive E).Free
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding utf8
$record | ConvertTo-Json -Depth 6
