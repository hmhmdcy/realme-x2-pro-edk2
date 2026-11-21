<#
Install the complete Plasma Mobile app bundle already staged on the phone.

Usage:
    powershell -ExecutionPolicy Bypass -File install-phone-apps.ps1

The SSH session is interactive because sudo asks for the phone user's
password.  Nothing is written to boot, logdump, DTB or userdata.
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "172.16.42.1",
    [string]$User = "user",
    [string]$Key = "$HOME\.ssh\samurai_id_ed25519",
    [string]$Bundle = "/home/user/plasma-apps-20261117"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Key -PathType Leaf)) {
    throw "SSH identity not found: $Key"
}

$knownHosts = "$HOME\.ssh\samurai_apps_known_hosts"
$common = @(
    "-i", $Key,
    "-o", "IdentitiesOnly=yes",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "UserKnownHostsFile=$knownHosts",
    "-o", "ConnectTimeout=8"
)

& ssh @common "$User@$HostAddress" "test -d '$Bundle/apks'"
if ($LASTEXITCODE -ne 0) {
    throw "App bundle not found on phone: $Bundle"
}

& ssh -t @common "$User@$HostAddress" `
    "sudo sh '$Bundle/install-plasma-apps.sh' '$Bundle'"
if ($LASTEXITCODE -ne 0) {
    throw "Application install failed"
}

& ssh @common "$User@$HostAddress" "'$Bundle/check-plasma-apps.sh'"
if ($LASTEXITCODE -ne 0) {
    throw "Post-install application check failed"
}
