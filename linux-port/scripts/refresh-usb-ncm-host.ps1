param(
    [string]$InterfaceDescription = "*UsbNcm*"
)

$ErrorActionPreference = "Stop"
$adapter = Get-NetAdapter |
    Where-Object InterfaceDescription -like $InterfaceDescription |
    Select-Object -First 1

if (-not $adapter) {
    throw "No matching USB NCM adapter found"
}

Write-Host "Adapter: $($adapter.Name) [$($adapter.InterfaceDescription)]"
Write-Host "Status:  $($adapter.Status), $($adapter.LinkSpeed)"

# ipconfig accepts the localized adapter name, unlike netsh's unstable
# numeric-interface syntax across Windows releases.
& ipconfig.exe /renew $adapter.Name

Start-Sleep -Seconds 5
Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 |
    Format-Table -AutoSize InterfaceAlias, IPAddress, PrefixLength, AddressState
