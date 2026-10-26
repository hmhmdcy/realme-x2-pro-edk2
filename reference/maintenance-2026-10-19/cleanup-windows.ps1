param([switch]$Apply)
$ErrorActionPreference='Stop'
$buildRoot=[IO.Path]::GetFullPath('E:\edk2-samurai-out')
$receiptRoot=Join-Path $buildRoot 'cleanup20261019'
New-Item -ItemType Directory -Path $receiptRoot -Force | Out-Null
$receiptPath=Join-Path $receiptRoot 'windows-cleanup-private.json'
function Assert-Within([string]$path) {
    $full=[IO.Path]::GetFullPath($path)
    if(-not $full.StartsWith($buildRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside explicit build root'}
    $item=Get-Item -LiteralPath $full -Force
    if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse point refused'}
    return $item
}
function Free-Bytes { return [ordered]@{C=(Get-PSDrive C).Free;E=(Get-PSDrive E).Free} }
if(-not $Apply) {
    if(Test-Path -LiteralPath $receiptPath){throw 'Receipt already exists'}
    $protected=@(
        @('kernel298\Image-k298-private','eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf'),
        @('kernel298\logdump-k298-candidate-private.img','dfef7be4f358c5c16e8e716a60c24da8a139de73b1e07912d70f2b58613d80df'),
        @('kernel298\modules-k298-private.tar.gz','3e032ab41517b32ed84b877232c9ce8f115813122d6f659e4361a72fa46411d4'),
        @('kernel290\logdump-k290-candidate-private.img','0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a'),
        @('kernel290\modules-k290-private.tar.gz','346754d0a8a4077f44546770788fe53b5b5f2ddefe259f0f4ab56c8397888587'),
        @('kernel302\ipa-bundle-r2-private.tar.gz','a12020406954ba8663d92a53155445a8b04c532172392e428be9f109baa66c94'),
        @('kernel132\samurai-rootfs-f2fs-k132-device-fixed.simg','290e7af5fdda219a558032f4f75dfec6979a32e66693f117964361a4fd903ccb')
    )
    foreach($row in $protected){$item=Assert-Within (Join-Path $buildRoot $row[0]);if((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row[1]){throw 'Protected artifact mismatch'}}
    $selected=@()
    foreach($rel in @('kernel282\host-pip-cache-preserved','kernel284\host-npm-cache-preserved')) {
        $item=Assert-Within (Join-Path $buildRoot $rel)
        $selected+=Get-ChildItem -LiteralPath $item.FullName -File -Recurse -Force
    }
    $selected+=Get-ChildItem -LiteralPath $buildRoot -File -Recurse -Filter vmlinux | Where-Object {$_.FullName -match '\\completed-[^\\]+\\vmlinux$' -and $_.FullName -notmatch '\\completed-boot290\\'}
    $rows=@($selected | ForEach-Object {$item=Assert-Within $_.FullName;[ordered]@{path=$item.FullName;bytes=$item.Length;mtime_ticks=$item.LastWriteTimeUtc.Ticks;removed=$false}})
    $ledger=[ordered]@{started_utc=[DateTime]::UtcNow.ToString('o');free_before=(Free-Bytes);protected=$protected;rows=$rows;bytes=($selected|Measure-Object Length -Sum).Sum;complete=$false}
    $ledger | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    [pscustomobject]@{Count=$rows.Count;Bytes=$ledger.bytes;Protected=$protected.Count} | ConvertTo-Json
} else {
    $ledger=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json -AsHashtable
    if($ledger.complete){throw 'Already applied'}
    foreach($row in $ledger.rows) {
        $item=Assert-Within $row.path
        if($item.PSIsContainer -or $item.Length -ne $row.bytes -or $item.LastWriteTimeUtc.Ticks -ne $row.mtime_ticks){throw 'Selected artifact changed'}
        if($item.FullName -notmatch '\\host-(pip|npm)-cache-preserved\\' -and $item.FullName -notmatch '\\completed-[^\\]+\\vmlinux$'){throw 'Allowlist mismatch'}
        Remove-Item -LiteralPath $item.FullName -Force
        $row.removed=$true
    }
    foreach($row in $ledger.protected){$item=Assert-Within (Join-Path $buildRoot $row[0]);if((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row[1]){throw 'Protected artifact changed'}}
    $ledger.complete=$true;$ledger.free_after=Free-Bytes;$ledger.finished_utc=[DateTime]::UtcNow.ToString('o')
    $ledger | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    [pscustomobject]@{Count=$ledger.rows.Count;Bytes=$ledger.bytes;FreeAfter=$ledger.free_after;Complete=$ledger.complete} | ConvertTo-Json
}
