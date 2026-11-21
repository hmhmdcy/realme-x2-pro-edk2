<#
Transfer a file over the rootfs NCM link in both directions and compare
hashes.  Windows PowerShell has no input redirection for native commands, so
scp is used rather than `ssh ... < file`.

Usage:
    test-ncm-throughput.ps1
    test-ncm-throughput.ps1 -Megabytes 8 -Rounds 3
#>

[CmdletBinding()]
param(
    [int]$Megabytes = 4,
    [int]$Rounds = 3,
    [string]$HostAddress = "172.16.42.1",
    [string]$User = "user",
    [string]$Key = "C:\Users\cy122\.ssh\samurai_id_ed25519",
    [string]$KnownHosts = "C:\Users\cy122\.ssh\samurai_ncm_known_hosts",
    [string]$OutDir = "E:\edk2-samurai-out\ncm-throughput"
)

$ErrorActionPreference = "Stop"
$scp = "C:\Windows\System32\OpenSSH\scp.exe"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$common = @(
    "-F", "NUL",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=$KnownHosts",
    "-i", $Key
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$local = Join-Path $OutDir ("probe-{0}MiB.bin" -f $Megabytes)
if (-not (Test-Path $local) -or (Get-Item $local).Length -ne $Megabytes * 1MB) {
    if (Test-Path $local) { Remove-Item $local -Force }
    $fs = [System.IO.File]::Create($local)
    $buffer = New-Object byte[] (1024 * 1024)
    for ($i = 0; $i -lt $Megabytes; $i++) {
        for ($j = 0; $j -lt $buffer.Length; $j++) {
            $buffer[$j] = [byte]((($i * 31) + ($j * 7)) % 251)
        }
        $fs.Write($buffer, 0, $buffer.Length)
    }
    $fs.Dispose()
}
$localHash = (Get-FileHash $local -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "local file: $Megabytes MiB sha256=$localHash"

$failures = 0
for ($round = 1; $round -le $Rounds; $round++) {
    $upFile = "/tmp/up-$round.bin"
    $downFile = Join-Path $OutDir "down-$round.bin"

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $scp @common $local "${User}@${HostAddress}:$upFile" 2>&1 | Out-Null
    $upSeconds = $sw.Elapsed.TotalSeconds

    $deviceHash = (& $ssh @common "${User}@${HostAddress}" "sha256sum $upFile") -split " " |
        Select-Object -First 1
    $upOk = $deviceHash -eq $localHash
    $upMbps = if ($upSeconds -gt 0) { [math]::Round(($Megabytes * 8) / $upSeconds, 1) } else { 0 }
    Write-Host ("round {0} up:   {1:N2}s  {2} Mb/s  hash {3}" -f
        $round, $upSeconds, $upMbps, $(if ($upOk) { "OK" } else { "MISMATCH" }))
    if (-not $upOk) { $failures++ }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $scp @common "${User}@${HostAddress}:$upFile" $downFile 2>&1 | Out-Null
    $downSeconds = $sw.Elapsed.TotalSeconds
    $downHash = (Get-FileHash $downFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $downOk = $downHash -eq $localHash
    $downMbps = if ($downSeconds -gt 0) { [math]::Round(($Megabytes * 8) / $downSeconds, 1) } else { 0 }
    Write-Host ("round {0} down: {1:N2}s  {2} Mb/s  hash {3}" -f
        $round, $downSeconds, $downMbps, $(if ($downOk) { "OK" } else { "MISMATCH" }))
    if (-not $downOk) { $failures++ }
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host "RESULT: FAIL ($failures transfer(s) mismatched)"
    exit 1
}
Write-Host "RESULT: PASS - $Rounds x $Megabytes MiB each way, hashes match"
exit 0
