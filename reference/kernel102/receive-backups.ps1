$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel102'
$target="$out\backup-chunks"
if (!(Test-Path -LiteralPath $target)) {New-Item -ItemType Directory -Path $target | Out-Null}
if (!(Test-Path -LiteralPath "$target\SHA256SUMS")) {
    & "$PSScriptRoot\scp-private.ps1" 'root@169.254.42.1:/tmp/k102-backup-chunks/SHA256SUMS' "$target\SHA256SUMS"
}
foreach ($line in (Get-Content -LiteralPath "$target\SHA256SUMS")) {
    if ($line -notmatch '^([a-f0-9]{64})  ((boot|logdump)-[0-9]{3}\.bin)$') {throw 'Unexpected chunk manifest'}
    $digest=$Matches[1];$name=$Matches[2]
    if (Test-Path -LiteralPath "$target\$name") {
        if ((Get-Item -LiteralPath "$target\$name").Length -eq 2097152 -and (Get-FileHash -LiteralPath "$target\$name").Hash.ToLowerInvariant() -eq $digest) {continue}
        $partial="$target\$name.partial-first"
        if (Test-Path -LiteralPath $partial) {throw 'Another incomplete transfer needs a fresh suffix'}
        Move-Item -LiteralPath "$target\$name" -Destination $partial
    }
    & "$PSScriptRoot\scp-private.ps1" "root@169.254.42.1:/tmp/k102-backup-chunks/$name" "$target\$name"
    if ((Get-Item -LiteralPath "$target\$name").Length -ne 2097152 -or (Get-FileHash -LiteralPath "$target\$name").Hash.ToLowerInvariant() -ne $digest) {throw 'Chunk hash/size mismatch'}
}
foreach ($spec in @(@('boot',48,'boot-partition-before.img'),@('logdump',32,'logdump-before.img'))) {
    $name=$spec[0];$count=$spec[1];$destination="$out\$($spec[2])"
    if (Test-Path -LiteralPath $destination) {throw 'Do not overwrite prior backup'}
    $stream=[System.IO.File]::Open($destination,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write)
    try {
        for ($index=0;$index -lt $count;$index++) {
            $chunk="$target\$name-$('{0:D3}' -f $index).bin"
            $bytes=[System.IO.File]::ReadAllBytes($chunk)
            $stream.Write($bytes,0,$bytes.Length)
        }
    } finally {$stream.Dispose()}
}
Write-Output 'FULL_BACKUPS_REASSEMBLED_FROM_VERIFIED_CHUNKS'
