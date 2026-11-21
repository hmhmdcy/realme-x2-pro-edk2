$ErrorActionPreference = "Stop"
$base = "E:\edk2-samurai-out\charging-management-20261023"
$temp = "C:\Users\cy122\AppData\Local\Temp"
$targets = @()

foreach ($number in 6..12) {
    $suffix = "{0:D2}" -f $number
    $targets += Join-Path $base "charging-integration-trial-20261027-r9-status-precharge-$suffix"
    $targets += Join-Path $base "charging-integration-trial-20261027-r9-status-precharge-$suffix-upload.tar"
}
$targets += @(
    Get-ChildItem -LiteralPath $base -File |
        Where-Object {
            $_.Name -match "^(frozen-r14-|test-results-frozen-0[56]-|test-run-frozen-0[56]-)"
        } |
        ForEach-Object FullName
)

$resolved = @()
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) {
        continue
    }
    $path = (Resolve-Path -LiteralPath $target).ProviderPath
    if (-not $path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside package root: $path"
    }
    $resolved += $path
}

$before = (Get-PSDrive E).Free
foreach ($path in $resolved) {
    Remove-Item -LiteralPath $path -Recurse -Force
}

$tempTargets = @(
    Get-ChildItem -LiteralPath $temp -Force |
        Where-Object {
            $_.Name -match "^(samurai-r9-review-|trial-tests-r4\.json$|trial-516-|trial516-tests-final\.log$|make_r4_debug\.py$|charging-trial-516-)"
        }
)
$tempPrefix = $temp + "\"
foreach ($item in $tempTargets) {
    $path = $item.FullName
    if (-not $path.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside temp: $path"
    }
    Remove-Item -LiteralPath $path -Recurse -Force
}

$after = (Get-PSDrive E).Free
[pscustomobject]@{
    removed_package_artifacts = $resolved.Count
    removed_temp_artifacts = $tempTargets.Count
    e_reclaimed_mib = [Math]::Round(($after - $before) / 1MB, 2)
    e_free_gib = [Math]::Round($after / 1GB, 2)
} | Format-List
