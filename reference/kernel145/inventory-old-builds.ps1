$ErrorActionPreference = 'Stop'
$buildRoot = [IO.Path]::GetFullPath('E:\edk2-samurai-out')
$report = Join-Path $buildRoot 'kernel145\old-build-inventory-private.json'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class SamuraiFileAllocation {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern uint GetCompressedFileSizeW(string path, out uint high);
}
'@
$files = @(rg --files --hidden --no-ignore $buildRoot)
if ($LASTEXITCODE -ne 0) { throw 'Inventory failed' }
$rows = foreach ($file in $files) {
    $path = [IO.Path]::GetFullPath($file)
    if (-not $path.StartsWith($buildRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Inventory escaped build output' }
    $item = Get-Item -LiteralPath $path
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
    $relative = $path.Substring($buildRoot.Length + 1)
    [uint32]$high = 0
    $low = [SamuraiFileAllocation]::GetCompressedFileSizeW($path, [ref]$high)
    if (($low -eq [uint32]::MaxValue) -and ([Runtime.InteropServices.Marshal]::GetLastWin32Error() -ne 0)) { throw 'Allocation query failed' }
    [pscustomobject]@{Path=$path;Relative=$relative;Stage=$relative.Split('\')[0];Name=$item.Name;Bytes=$item.Length;AllocatedBytes=([uint64]$high -shl 32) -bor [uint64]$low;ModifiedUtc=$item.LastWriteTimeUtc.ToString('o')}
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $report -Encoding utf8
$rows | Group-Object Stage | ForEach-Object { [pscustomobject]@{Stage=$_.Name;Bytes=($_.Group | Measure-Object Bytes -Sum).Sum;AllocatedBytes=($_.Group | Measure-Object AllocatedBytes -Sum).Sum} } | Sort-Object AllocatedBytes -Descending | Select-Object -First 15 | Format-Table -AutoSize
$rows | Sort-Object AllocatedBytes -Descending | Select-Object -First 30 Stage,Name,Bytes,AllocatedBytes | Format-Table -AutoSize
