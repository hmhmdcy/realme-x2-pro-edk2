$ErrorActionPreference='Stop'
$adapters=@(Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -and $_.InterfaceDescription -match '^UsbNcm Host Device' -and $_.PnPDeviceID -match 'VID_0525&PID_A4A1'})
if ($adapters.Count -ne 1) {throw 'A single verified running Samurai NCM adapter is required'}
$adapter=$adapters[0]
$before=Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4
$before | Select-Object IPAddress,PrefixLength,PrefixOrigin | ConvertTo-Json | Set-Content -LiteralPath 'E:/edk2-samurai-out/kernel115/usb-host-address-before-private.json'
if (!@($before | Where-Object {$_.IPAddress -eq '169.254.42.2' -and $_.PrefixLength -eq 24}).Count) {
    New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress '169.254.42.2' -PrefixLength 24 -AddressFamily IPv4 -ErrorAction Stop | Out-Null
}
if (!@(Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 | Where-Object {$_.IPAddress -eq '169.254.42.2' -and $_.PrefixLength -eq 24}).Count) {throw 'NCM host address was not applied'}
Write-Output 'VERIFIED_SAMURAI_NCM_HOST_ADDRESS_169_254_42_2_CONFIGURED'
