<#
Repeat a raw-TCP (no SSH) device-to-host transfer and hash every result.

Start a fresh `nc` listener on the device before each round and read the
whole stream with TcpClient.  A short read or wrong hash here would mean
loss below SSH; SSH/scp failures alone point at the SSH transport.
#>

[CmdletBinding()]
param(
    [int]$Rounds = 8,
    [int]$Port = 9001,
    [string]$RemoteFile = "/tmp/up-1.bin",
    [int64]$ExpectedBytes = 33554432,
    [string]$ExpectedSha256 = "ad793b699ac0cda52cd8cb1e8cc19419c8d2852d1f750e5a293868f0fe7ee143",
    [string]$HostAddress = "172.16.42.1",
    [string]$User = "user",
    [string]$Key = "C:\Users\cy122\.ssh\samurai_id_ed25519",
    [string]$KnownHosts = "C:\Users\cy122\.ssh\samurai_ncm_known_hosts",
    [string]$OutDir = "E:\edk2-samurai-out\ncm-raw"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$sshArgs = @("-F", "NUL", "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=$KnownHosts", "-i", $Key, "${User}@${HostAddress}")
$reader = Join-Path $PSScriptRoot "raw-tcp-read.ps1"

$ok = 0
$bad = 0
for ($i = 1; $i -le $Rounds; $i++) {
    $listen = "setsid sh -c 'exec nc -l -p $Port < $RemoteFile' >/dev/null 2>&1 < /dev/null & sleep 1; ss -ltn"
    & $ssh @sshArgs $listen 2>&1 | Out-Null
    $dest = Join-Path $OutDir "raw-$i.bin"
    if (Test-Path $dest) { Remove-Item $dest -Force }
    $line = & $reader -Port $Port -ExpectedBytes $ExpectedBytes -OutFile $dest 2>&1 |
        Select-Object -Last 1
    $hash = (Get-FileHash $dest -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash
    $match = $hash -and ($hash.ToLowerInvariant() -eq $ExpectedSha256)
    if ($match) { $ok++ } else { $bad++ }
    Write-Host ("{0,2}: {1}  hash={2}" -f
        $i, $line, $(if ($match) { "OK" } else { "BAD" }))
    Remove-Item $dest -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "raw TCP: rounds=$Rounds ok=$ok bad=$bad"
if ($bad -gt 0) {
    Write-Host "RESULT: FAIL - loss occurs below SSH"
    exit 1
}
Write-Host "RESULT: PASS - USB/NCM delivers every byte; earlier failures were SSH-level"
exit 0
