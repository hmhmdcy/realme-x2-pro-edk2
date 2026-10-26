$ErrorActionPreference = 'Stop'
$taskVolumePath = [IO.Path]::GetFullPath('E:\edk2-samurai-out\kernel134\build-volume.ext4')
if ($taskVolumePath -cne 'E:\edk2-samurai-out\kernel134\build-volume.ext4') { throw 'Wrong fixed private volume' }
$taskInventory = Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel134\zero-range-inventory-private.json' -Raw | ConvertFrom-Json
if ($taskInventory.fixed_windows_target -cne $taskVolumePath -or -not $taskInventory.all_ranges_verified_byte_zero) { throw 'Invalid verified inventory target' }
if ((Get-Item -LiteralPath $taskVolumePath).Length -ne $taskInventory.image_bytes) { throw 'Volume length changed' }
if (Test-Path -LiteralPath 'E:\edk2-samurai-out\kernel134\windows-zero-range-operations-private.json') { throw 'Single-use zero range operation already ran' }
Add-Type -TypeDefinition @'
using System;
using System.IO;
public static class SamuraiFixedZeroRangeVerifier {
    public static bool IsZero(string path, long offset, long length) {
        using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read)) {
            stream.Seek(offset, SeekOrigin.Begin);
            var buffer = new byte[1024 * 1024];
            while (length > 0) {
                int wanted = (int)Math.Min(length, buffer.Length);
                int total = 0;
                while (total < wanted) {
                    int read = stream.Read(buffer, total, wanted - total);
                    if (read == 0) throw new IOException("Unexpected end of fixed volume");
                    total += read;
                }
                for (int i = 0; i < wanted; i++) if (buffer[i] != 0) return false;
                length -= wanted;
            }
            return true;
        }
    }
}
'@
$taskBeforeFree = (Get-PSDrive -Name E).Free
$taskDone = 0
$taskExit = 0
foreach ($taskRange in $taskInventory.ranges) {
    $taskOffset = [long]$taskRange.offset
    $taskLength = [long]$taskRange.length
    if ($taskOffset -lt 0 -or $taskLength -le 0 -or $taskOffset -gt ([long]$taskInventory.image_bytes - $taskLength)) { throw 'Zero range out of bounds' }
    if (-not [SamuraiFixedZeroRangeVerifier]::IsZero($taskVolumePath, $taskOffset, $taskLength)) { throw 'Range is no longer byte-zero; refuse sparse mutation' }
    fsutil sparse setrange $taskVolumePath $taskOffset $taskLength >> 'E:\edk2-samurai-out\kernel134\windows-zero-range-operations-private.txt' 2>&1
    if ($LASTEXITCODE -ne 0) { $taskExit = $LASTEXITCODE; break }
    $taskDone++
}
@{ verified_range_count=$taskInventory.ranges.Count; completed_range_count=$taskDone; native_exit=$taskExit;
   fixed_target=$taskVolumePath; windows_e_free_before_bytes=$taskBeforeFree;
   windows_e_free_after_bytes=(Get-PSDrive -Name E).Free } | ConvertTo-Json | Set-Content -LiteralPath 'E:\edk2-samurai-out\kernel134\windows-zero-range-operations-private.json'
Write-Output "K134_WINDOWS_ZERO_ONLY_RANGE_OPERATIONS_TERMINAL $taskDone $taskExit"
