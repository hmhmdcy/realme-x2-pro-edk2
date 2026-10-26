$ErrorActionPreference='Stop'
$workspace='E:/RealmeX2Pro edk2'
$outputRoot='E:/edk2-samurai-out/kernel149'
$index=Get-Content -LiteralPath "$workspace/reference/kernel149/archive-index.json" -Raw | ConvertFrom-Json
$verified=@()
foreach($entry in $index.archives) {
    if($entry.label -notmatch '^[a-z0-9-]+$' -or $entry.name -notmatch '^k149-[a-z0-9-]+-private\.tar\.gz$') {throw 'Unexpected archive name'}
    $destination=Join-Path $outputRoot "$($entry.label)-private.tar.gz"
    if(!(Test-Path -LiteralPath $destination)) {
        & "$workspace/reference/kernel109/scp-pmos.ps1" -Source "root@169.254.42.1:/var/lib/samurai/k149-private-archives/$($entry.name)" -Destination $destination
    }
    $actual=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if($actual -ne $entry.sha256) {throw "Archive mismatch: $($entry.label)"}
    $verified+=@{label=$entry.label;bytes=(Get-Item -LiteralPath $destination).Length;sha256=$actual}
}
$report=@{all_raw_archives_downloaded=$true;archives_verified=$verified.Count;verified=$verified}
$report | ConvertTo-Json -Depth 5 | Out-File -LiteralPath "$workspace/reference/kernel149/host-archive-verification.json" -Encoding utf8NoBOM
"K149_HOST_ARCHIVES_VERIFIED=$($verified.Count)"
