<#
Switch USB gadget mode developer -> tethering -> developer and assert the
device stays reachable at every step.

The failure this guards against: a tethering switch left usb0 with no address
and 0 received bytes, so SSH died and the only remote maintenance path was
gone.  Every step here re-runs the link check after the switch settles.

Requires SSH access at the start (developer mode).
#>

[CmdletBinding()]
param(
    [string]$HostAddress = "172.16.42.1",
    [string]$LinkLocal = "169.254.42.1",
    [string]$TetherHost = "10.42.0.1",
    [string]$User = "user",
    [string]$Key = "C:\Users\cy122\.ssh\samurai_id_ed25519",
    [string]$KnownHosts = "C:\Users\cy122\.ssh\samurai_ncm_known_hosts",
    [string]$Password = "",
    [int]$SettleSeconds = 25
)

$ErrorActionPreference = "Stop"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$common = @("-F", "NUL", "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=$KnownHosts", "-o", "ConnectTimeout=10",
    "-i", $Key)
$verify = Join-Path $PSScriptRoot "verify-ncm-rootfs-link.ps1"
$failures = @()

# The maintenance path must stay reachable in every mode, so every SSH
# attempt tries the mode's own address and then the link-local fallback.
function Ssh-Addresses {
    param([string]$Primary)
    return @($Primary, $LinkLocal)
}

function Set-UsbMode {
    param([string]$Mode)
    $pw = if ($Password) { "echo $Password | sudo -S " } else { "sudo -S " }
    foreach ($address in Ssh-Addresses $HostAddress) {
        & $ssh @common "${User}@${address}" "$pw dbus-send --system --type=method_call --print-reply " +
            "--dest=com.meego.usb_moded /com/meego/usb_moded " +
            "com.meego.usb_moded.set_mode string:$Mode" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { return }
    }
}

function Check-Link {
    param([string]$Label, [string]$Server, [string]$Client)
    Write-Host ""
    Write-Host "== $Label =="
    & $verify -TimeoutSeconds 40 -Server $Server -ClientExpected $Client `
        -LinkLocal $LinkLocal -SkipSsh 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        $failures += $Label
        Write-Host "FAIL: $Label did not keep the link usable" -ForegroundColor Red
        return $false
    }
    return $true
}

function Check-Ssh {
    param([string]$Label, [string[]]$Addresses = @($HostAddress))
    foreach ($address in ($Addresses + $LinkLocal)) {
        $out = & $ssh @common "${User}@${address}" "echo ssh-ok; cat /run/samurai-usb-network.mode" 2>&1
        $text = ($out -join "`n")
        if ($text -match "ssh-ok") {
            Write-Host "OK   $Label ssh reachable via $address ($($text -split "`n" | Select-Object -Last 1))"
            return $true
        }
    }
    Write-Host "FAIL $Label ssh unreachable via $($Addresses -join ',') or $LinkLocal"
    $failures += "$Label (ssh)"
    return $false
}

if (-not (Check-Ssh "initial developer mode" @($HostAddress))) {
    Write-Host "RESULT: FAIL - cannot even start; device is not in a reachable developer mode"
    exit 1
}

if (-not (Check-Link "initial developer mode" "172.16.42.1" "172.16.42.2")) { exit 1 }

Write-Host ""
Write-Host "switching to tethering_mode"
Set-UsbMode "tethering_mode"
Start-Sleep -Seconds $SettleSeconds
$null = Check-Link "tethering mode" $TetherHost "10.42.0.2"
if (-not (Check-Ssh "tethering mode" @($TetherHost))) {
    Write-Host "tethering lost SSH; restoring developer mode before exit" -ForegroundColor Yellow
    Set-UsbMode "developer_mode"
    Start-Sleep -Seconds $SettleSeconds
    if (-not (Check-Ssh "developer mode (rollback)" @($HostAddress))) {
        Write-Host "RESULT: FAIL - tethering stranded the device and rollback could not reach it"
        exit 1
    }
    Write-Host "RESULT: FAIL - tethering was not usable, device rolled back to developer mode"
    exit 1
}

Write-Host ""
Write-Host "switching back to developer_mode"
Set-UsbMode "developer_mode"
Start-Sleep -Seconds $SettleSeconds
$null = Check-Link "developer mode (restored)" "172.16.42.1" "172.16.42.2"
$null = Check-Ssh "developer mode (restored)" @($HostAddress)

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "RESULT: FAIL"
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "RESULT: PASS - developer <-> tethering round trip keeps the device reachable"
exit 0
