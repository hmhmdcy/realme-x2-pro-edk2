$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath('E:\edk2-samurai-out\kernel134\samurai-rootfs-f2fs-k134-device-fixed.simg')
$targetRoot = [IO.Path]::GetFullPath('C:\Users\cy122\.codex\work-output\realme-x2-pro-private\kernel134')
$target = [IO.Path]::GetFullPath((Join-Path $targetRoot 'samurai-rootfs-f2fs-k134-device-fixed.simg'))
$manifest = 'E:\edk2-samurai-out\kernel144\relocated-rejected134-image-private.json'
if ($source -ne 'E:\edk2-samurai-out\kernel134\samurai-rootfs-f2fs-k134-device-fixed.simg') { throw 'Unexpected source' }
if (-not $target.StartsWith($targetRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Target escaped private output' }
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $manifest)) { throw 'Inspect any previous relocation before retry' }
$size = (Get-Item -LiteralPath $source).Length
if ($size -ne 1817957988) { throw 'Unexpected rejected image size' }
if ((Get-PSDrive -Name C).Free -lt ($size + 1GB)) { throw 'Insufficient destination capacity' }
$hashBefore = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $target
if ((Get-Item -LiteralPath $target).Length -ne $size) { throw 'Destination size mismatch' }
$hashAfter = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hashBefore -ne $hashAfter) { throw 'Destination checksum mismatch; source preserved' }
$record = [ordered]@{ stage=144; source=$source; target=$target; bytes=$size; sha256=$hashBefore; destination_verified=$true; source_removed=$false; phone_modified=$false }
$record | ConvertTo-Json | Set-Content -LiteralPath $manifest -Encoding utf8
if ([IO.Path]::GetFullPath($source) -ne 'E:\edk2-samurai-out\kernel134\samurai-rootfs-f2fs-k134-device-fixed.simg') { throw 'Removal path mismatch' }
Remove-Item -LiteralPath $source
$record.source_removed = $true
$record | ConvertTo-Json | Set-Content -LiteralPath $manifest -Encoding utf8
Write-Output ('K144_REJECTED134_IMAGE_RELOCATED_HASH_VERIFIED_E_FREE_BYTES=' + (Get-PSDrive -Name E).Free)
