[CmdletBinding()]
param(
    [string]$FastbootPath = 'C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe',
    [Parameter(Mandatory = $true)]
    [string]$StageReceipt,
    [string]$ManifestPath = (Join-Path $PSScriptRoot 'manifest.json'),
    [string]$WorkDirectory = '',
    [string]$ReportPath = '',
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
$script:Serial = '62bc28a1'
$script:Product = 'msmnile'
$script:Commands = [System.Collections.Generic.List[object]]::new()
$script:WriteAttempted = $false
$script:RebootAttempted = $false
$script:RecoveryAttempted = $false

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-True {
    param([object]$Value, [string]$Name)
    if ($Value -ne $true) {
        throw "$Name must be true"
    }
}

function Assert-False {
    param([object]$Value, [string]$Name)
    if ($Value -ne $false) {
        throw "$Name must be false"
    }
}

function Assert-FilePin {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Sha256,
        [Parameter(Mandatory = $true)][long]$Bytes,
        [string]$Label = 'file'
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label is missing: $Path"
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne $Bytes) {
        throw "$Label size mismatch: $($item.Length) != $Bytes"
    }
    $actual = Get-Sha256 -Path $Path
    if ($actual -ne $Sha256.ToLowerInvariant()) {
        throw "$Label hash mismatch: $actual != $Sha256"
    }
}

function Invoke-Fastboot {
    param(
        [string[]]$Arguments = @(),
        [switch]$AllowFailure,
        [switch]$Devices
    )
    if ($Devices) {
        $argv = @('devices')
    }
    else {
        $argv = @('-s', $script:Serial) + $Arguments
    }
    $display = @($FastbootPath) + $argv
    $script:Commands.Add([pscustomobject]@{
        argv = $display
        started = $true
    })
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $FastbootPath @argv 2>&1
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }
    $text = (@($output) | ForEach-Object { $_.ToString() }) -join "`n"
    $script:Commands.Add([pscustomobject]@{
        argv = $display
        exit_code = $code
        output = $text
    })
    if (-not $AllowFailure -and $code -ne 0) {
        throw "fastboot failed ($code): $($argv -join ' ')`n$text"
    }
    [pscustomobject]@{
        ExitCode = $code
        Text = $text
    }
}

function Get-DeviceSerial {
    $result = Invoke-Fastboot -Arguments @() -Devices
    if ($result.ExitCode -ne 0) {
        throw "fastboot devices failed`n$($result.Text)"
    }
    $lines = @(
        $result.Text -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and ($_ -match '\bfastboot\b') }
    )
    if ($lines.Count -ne 1) {
        throw "expected exactly one fastboot device, found $($lines.Count)"
    }
    $entry = ($lines[0] -split '\s+')
    if ($entry.Count -lt 2) {
        throw "cannot parse fastboot devices output: $($lines[0])"
    }
    $serial = $entry[0].ToLowerInvariant()
    if ($serial -ne $script:Serial) {
        throw "unexpected device serial: $serial"
    }
    $serial
}

function Get-Var {
    param([Parameter(Mandatory = $true)][string]$Name)
    $result = Invoke-Fastboot -Arguments @('getvar', $Name)
    if ($result.ExitCode -ne 0) {
        throw "fastboot getvar $Name failed`n$($result.Text)"
    }
    $result.Text
}

function Assert-Product {
    $text = Get-Var -Name 'product'
    if ($text -notmatch '(?im)(?:\(bootloader\)\s*)?product:\s*msmnile(?:\s|$)') {
        throw "unexpected fastboot product`n$text"
    }
}

function Parse-PartitionSize {
    param([string]$Text, [string]$Partition)
    $pattern = '(?im)(?:\(bootloader\)\s*)?partition-size:' +
        [regex]::Escape($Partition) +
        ':\s*(0x[0-9a-f]+|[0-9]+)'
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) {
        throw "cannot parse partition-size:$Partition`n$Text"
    }
    $word = $match.Groups[1].Value
    if ($word.StartsWith('0x', [System.StringComparison]::OrdinalIgnoreCase)) {
        [Convert]::ToInt64($word.Substring(2), 16)
    }
    else {
        [Convert]::ToInt64($word, 10)
    }
}

function Assert-PartitionSizes {
    $bootText = Get-Var -Name 'partition-size:boot'
    $logText = Get-Var -Name 'partition-size:logdump'
    $boot = Parse-PartitionSize -Text $bootText -Partition 'boot'
    $logdump = Parse-PartitionSize -Text $logText -Partition 'logdump'
    if ($boot -ne [long]$Manifest.carriers.boot.bytes) {
        throw "boot partition size mismatch: $boot"
    }
    if ($logdump -ne [long]$Manifest.carriers.logdump.bytes) {
        throw "logdump partition size mismatch: $logdump"
    }
    [pscustomobject]@{ boot = $boot; logdump = $logdump }
}

function Fetch-And-Verify {
    param(
        [Parameter(Mandatory = $true)][string]$Partition,
        [Parameter(Mandatory = $true)][string]$ExpectedSha,
        [Parameter(Mandatory = $true)][long]$Bytes,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $out = Join-Path $script:TrialWork $Label
    if (Test-Path -LiteralPath $out) {
        throw "refusing to overwrite readback file: $out"
    }
    $result = Invoke-Fastboot -Arguments @('fetch', $Partition, $out)
    if ($result.ExitCode -ne 0) {
        throw "fastboot fetch $Partition failed`n$($result.Text)"
    }
    if (-not (Test-Path -LiteralPath $out -PathType Leaf)) {
        throw "fastboot fetch did not create $out"
    }
    $item = Get-Item -LiteralPath $out
    if ($item.Length -ne $Bytes) {
        throw "$Label readback size mismatch: $($item.Length) != $Bytes"
    }
    $actual = Get-Sha256 -Path $out
    if ($actual -ne $ExpectedSha.ToLowerInvariant()) {
        throw "$Label readback hash mismatch: $actual != $ExpectedSha"
    }
    [pscustomobject]@{
        path = $out
        sha256 = $actual
        bytes = $item.Length
    }
}

function Flash-And-Verify {
    param(
        [Parameter(Mandatory = $true)][string]$Partition,
        [Parameter(Mandatory = $true)][string]$Image,
        [Parameter(Mandatory = $true)][string]$ExpectedSha,
        [Parameter(Mandatory = $true)][long]$Bytes,
        [Parameter(Mandatory = $true)][string]$Readback
    )
    $script:WriteAttempted = $true
    $result = Invoke-Fastboot -Arguments @('flash', $Partition, $Image)
    if ($result.ExitCode -ne 0) {
        throw "fastboot flash $Partition failed`n$($result.Text)"
    }
    Fetch-And-Verify -Partition $Partition -ExpectedSha $ExpectedSha -Bytes $Bytes -Label $Readback
}

function Invoke-SingleReboot {
    if ($script:RebootAttempted) {
        throw 'refusing to send fastboot reboot more than once'
    }
    $script:RebootAttempted = $true
    $result = Invoke-Fastboot -Arguments @('reboot') -AllowFailure
    if ($result.ExitCode -ne 0) {
        throw "fastboot reboot failed`n$($result.Text)"
    }
}

function Restore-OldPair {
    if ($script:RecoveryAttempted) {
        throw 'refusing to replay recovery more than once'
    }
    $script:RecoveryAttempted = $true
    if ($script:RebootAttempted) {
        throw 'refusing to write recovery after reboot was attempted'
    }
    $steps = @()
    # Match the guard's required order: old boot, then old logdump.
    $steps += Flash-And-Verify `
        -Partition 'boot' `
        -Image $Manifest.carriers.boot.old_path `
        -ExpectedSha $Manifest.carriers.boot.old `
        -Bytes ([long]$Manifest.carriers.boot.bytes) `
        -Readback 'recovery-boot.img'
    $steps += Flash-And-Verify `
        -Partition 'logdump' `
        -Image $Manifest.carriers.logdump.old_path `
        -ExpectedSha $Manifest.carriers.logdump.old `
        -Bytes ([long]$Manifest.carriers.logdump.bytes) `
        -Readback 'recovery-logdump.img'
    [pscustomobject]@{ passed = $true; steps = $steps }
}

function Test-StageReceipt {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "stage receipt is missing: $Path"
    }
    $receipt = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1) { throw 'stage receipt schema mismatch' }
    if ($receipt.trial_id -ne $Manifest.trial_id) { throw 'stage receipt trial id mismatch' }
    if ($receipt.version_pin -ne $Manifest.kernel_version) { throw 'stage receipt version pin mismatch' }
    if ($receipt.watch_seconds -ne $Manifest.watch_seconds) { throw 'stage receipt watch mismatch' }
    if ($receipt.serial.ToLowerInvariant() -ne $script:Serial) { throw 'stage receipt serial mismatch' }
    if (@('operator_cli', 'device_property') -notcontains $receipt.serial_source) {
        throw 'stage receipt serial source is missing or unsupported'
    }
    if ($receipt.restart_method -ne 'restart2_syscall_142') {
        throw 'stage receipt does not use the verified Restart2 bootloader path'
    }
    if ($receipt.restart2.syscall -ne 142 -or
        $receipt.restart2.magic1 -ne 4276215469 -or
        $receipt.restart2.magic2 -ne 672274793 -or
        $receipt.restart2.command -ne 'bootloader' -or
        $receipt.restart2.command_value -ne 2712847316 -or
        $receipt.restart2.attempt_count -ne 1 -or
        $receipt.restart2.retry -ne $false) {
        throw 'stage receipt Restart2 constants are invalid'
    }
    Assert-True $receipt.passed 'stage passed'
    Assert-True $receipt.stage_execute 'stage_execute'
    Assert-True $receipt.guard_installed 'guard_installed'
    Assert-True $receipt.original_service_installed 'original_service_installed'
    Assert-True $receipt.old_carriers_backed_up 'old_carriers_backed_up'
    Assert-True $receipt.partition_identity_recorded 'partition_identity_recorded'
    Assert-False $receipt.new_carrier_written 'new_carrier_written'
    Assert-True $receipt.reboot_bootloader_requested 'reboot_bootloader_requested'
    if ($receipt.manifest_sha256 -ne (Get-Sha256 -Path $ManifestPath)) {
        throw 'stage receipt manifest hash mismatch'
    }
    foreach ($property in $Manifest.device_files.PSObject.Properties) {
        $target = $property.Name
        $expected = $property.Value.sha256.ToLowerInvariant()
        $actualProperty = $receipt.installed_file_sha256.PSObject.Properties[$target]
        if ($null -eq $actualProperty) {
            throw "stage receipt lacks installed hash for $target"
        }
        if ($actualProperty.Value.ToLowerInvariant() -ne $expected) {
            throw "stage receipt installed hash mismatch for $target"
        }
    }
    foreach ($name in @('boot', 'logdump')) {
        if ($receipt.partition_identity.PSObject.Properties.Name -notcontains $name) {
            throw "stage receipt lacks partition identity for $name"
        }
        if ($receipt.old_carrier_sha256.$name -ne $Manifest.carriers.$name.old) {
            throw "stage receipt old hash mismatch for $name"
        }
    }
    $receipt
}

function Assert-Manifest {
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw "manifest is missing: $ManifestPath"
    }
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 1) { throw 'manifest schema mismatch' }
    if ($manifest.fastboot.serial -ne $script:Serial) { throw 'manifest serial mismatch' }
    if ($manifest.fastboot.product -ne $script:Product) { throw 'manifest product mismatch' }
    Assert-False $manifest.high_voltage_permitted 'high_voltage_permitted'
    foreach ($name in @('boot', 'logdump')) {
        $row = $manifest.carriers.$name
        Assert-FilePin -Path $row.old_path -Sha256 $row.old -Bytes ([long]$row.bytes) -Label "old $name"
        Assert-FilePin -Path $row.new_path -Sha256 $row.new -Bytes ([long]$row.bytes) -Label "new $name"
    }
    $manifest
}

$report = [ordered]@{
    schema = 1
    passed = $false
    execute = [bool]$Execute
    device_touched = $false
    writes_attempted = $false
    recovery_attempted = $false
    reboot_count = 0
    outcome = 'not_started'
    commands = $script:Commands
}

try {
    if (-not (Test-Path -LiteralPath $FastbootPath -PathType Leaf)) {
        throw "fastboot executable is missing: $FastbootPath"
    }
    $Manifest = Assert-Manifest
    $receipt = Test-StageReceipt -Path $StageReceipt
    $report.stage_receipt = $receipt

    if ([string]::IsNullOrWhiteSpace($WorkDirectory)) {
        $WorkDirectory = Join-Path ([System.IO.Path]::GetTempPath()) (
            'charging-trial-509-' + [guid]::NewGuid().ToString('N')
        )
    }
    if (Test-Path -LiteralPath $WorkDirectory) {
        if (@(Get-ChildItem -LiteralPath $WorkDirectory -Force).Count -ne 0) {
            throw "work directory must be new or empty: $WorkDirectory"
        }
    }
    else {
        New-Item -ItemType Directory -Path $WorkDirectory | Out-Null
    }
    $script:TrialWork = (Resolve-Path -LiteralPath $WorkDirectory).Path
    $report.work_directory = $script:TrialWork

    if (-not $Execute) {
        $report.passed = $true
        $report.outcome = 'local_validation_only'
        $report.device_touched = $false
        return
    }

    $report.device_touched = $true
    $serial = Get-DeviceSerial
    $report.serial = $serial
    Assert-Product
    $sizes = Assert-PartitionSizes
    $report.partition_sizes = $sizes

    $preflightBoot = Fetch-And-Verify `
        -Partition 'boot' `
        -ExpectedSha $Manifest.carriers.boot.old `
        -Bytes ([long]$Manifest.carriers.boot.bytes) `
        -Label 'preflight-boot.img'
    $preflightLogdump = Fetch-And-Verify `
        -Partition 'logdump' `
        -ExpectedSha $Manifest.carriers.logdump.old `
        -Bytes ([long]$Manifest.carriers.logdump.bytes) `
        -Label 'preflight-logdump.img'
    $report.preflight_current_old = @($preflightBoot, $preflightLogdump)

    try {
        $report.logdump = Flash-And-Verify `
            -Partition 'logdump' `
            -Image $Manifest.carriers.logdump.new_path `
            -ExpectedSha $Manifest.carriers.logdump.new `
            -Bytes ([long]$Manifest.carriers.logdump.bytes) `
            -Readback 'new-logdump.img'
        $report.boot = Flash-And-Verify `
            -Partition 'boot' `
            -Image $Manifest.carriers.boot.new_path `
            -ExpectedSha $Manifest.carriers.boot.new `
            -Bytes ([long]$Manifest.carriers.boot.bytes) `
            -Readback 'new-boot.img'
        Invoke-SingleReboot
        $report.reboot_count = 1
        $report.passed = $true
        $report.outcome = 'new_pair_verified_and_rebooted'
    }
    catch {
        $writeError = $_.Exception.Message
        $report.write_error = $writeError
        if (-not $script:WriteAttempted) {
            throw
        }
        try {
            $recovery = Restore-OldPair
            $report.recovery = $recovery
            $report.recovery_attempted = $true
            Invoke-SingleReboot
            $report.reboot_count = 1
            $report.outcome = 'old_pair_restored_and_rebooted'
        }
        catch {
            $report.recovery_error = $_.Exception.Message
            $report.recovery_attempted = $script:RecoveryAttempted
            $report.outcome = 'recovery_failed_no_reboot'
        }
    }
}
catch {
    $report.error = $_.Exception.Message
    if ($report.device_touched -and $report.outcome -eq 'not_started') {
        $report.outcome = 'failed_device_preflight'
    }
}
finally {
    $report.writes_attempted = $script:WriteAttempted
    $report.recovery_attempted = $script:RecoveryAttempted
    $report.reboot_attempted = $script:RebootAttempted
    $report.reboot_count = if ($script:RebootAttempted) { 1 } else { 0 }
    $json = $report | ConvertTo-Json -Depth 12
    if (-not [string]::IsNullOrWhiteSpace($ReportPath)) {
        $parent = Split-Path -Parent $ReportPath
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent | Out-Null
        }
        Set-Content -LiteralPath $ReportPath -Value $json -Encoding utf8
    }
    Write-Output $json
    if (-not $report.passed) {
        exit 3
    }
}
