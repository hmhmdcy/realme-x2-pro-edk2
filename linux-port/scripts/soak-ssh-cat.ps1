<#
Transfer with `ssh ... cat FILE` instead of scp/SFTP.

scp uses the SFTP subsystem.  This script streams the same file through a
plain SSH "exec" channel, so a difference in failure rate isolates the
fault to SFTP handling rather than to SSH, TCP or USB.
#>

[CmdletBinding()]
param(
    [int]$Rounds = 10,
    [string]$RemoteFile = "/tmp/up-1.bin",
    [int64]$ExpectedBytes = 33554432,
    [string]$ExpectedSha256 = "ad793b699ac0cda52cd8cb1e8cc19419c8d2852d1f750e5a293868f0fe7ee143",
    [string]$HostAddress = "172.16.42.1",
    [string]$User = "user",
    [string]$Key = "C:\Users\cy122\.ssh\samurai_id_ed25519",
    [string]$KnownHosts = "C:\Users\cy122\.ssh\samurai_ncm_known_hosts",
    [string]$OutDir = "E:\edk2-samurai-out\ncm-sshcat"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"

$ok = 0
$bad = 0
for ($i = 1; $i -le $Rounds; $i++) {
    $dest = Join-Path $OutDir "cat-$i.bin"
    if (Test-Path $dest) { Remove-Item $dest -Force }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $ssh
    $psi.Arguments = "-F NUL -o StrictHostKeyChecking=no " +
        "-o UserKnownHostsFile=`"$KnownHosts`" -i `"$Key`" " +
        "${User}@${HostAddress} `"cat $RemoteFile`""
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($psi)

    $fs = [System.IO.File]::Create($dest)
    $buffer = New-Object byte[] 262144
    [int64]$total = 0
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $src = $proc.StandardOutput.BaseStream
    while ($true) {
        $read = $src.Read($buffer, 0, $buffer.Length)
        if ($read -le 0) { break }
        $total += $read
        $fs.Write($buffer, 0, $read)
    }
    $sw.Stop()
    $fs.Dispose()
    $err = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit(10000) | Out-Null

    $hash = (Get-FileHash $dest -Algorithm SHA256).Hash.ToLowerInvariant()
    $match = $hash -eq $ExpectedSha256
    if ($match) { $ok++ } else { $bad++ }
    $mbps = if ($sw.Elapsed.TotalSeconds -gt 0) {
        [math]::Round(($total * 8 / 1000000) / $sw.Elapsed.TotalSeconds, 1)
    } else { 0 }
    Write-Host ("{0,2}: {1,6:N2}s {2,7} Mb/s bytes={3}/{4} hash={5}" -f
        $i, $sw.Elapsed.TotalSeconds, $mbps, $total, $ExpectedBytes,
        $(if ($match) { "OK" } else { "BAD" }))
    if ($err -and $err.Trim()) { Write-Host "    stderr: $($err.Trim())" }
    Remove-Item $dest -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "ssh-cat: rounds=$Rounds ok=$ok bad=$bad"
if ($bad -gt 0) {
    Write-Host "RESULT: FAIL - plain SSH channel also loses data"
    exit 1
}
Write-Host "RESULT: PASS - plain SSH channel is reliable (SFTP-specific fault)"
exit 0
