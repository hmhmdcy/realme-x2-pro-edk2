$ErrorActionPreference = 'Stop'
$taskPrivate = 'E:\edk2-samurai-out\kernel189'
$taskDeadline = (Get-Date).AddSeconds(40)
do {
    $taskAdapters = @(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -like 'UsbNcm Host Device*' })
    if ($taskAdapters.Count -eq 1) { break }
    if ((Get-Date) -ge $taskDeadline) { throw 'No unique current USB NCM interface yet' }
    Start-Sleep -Milliseconds 500
} while ($true)
$taskAdapter = $taskAdapters[0]
$taskPing = & C:\Windows\System32\PING.EXE -6 -n 2 -w 1000 ('ff02::1%' + $taskAdapter.InterfaceIndex)
$taskPing | Set-Content -LiteralPath "$taskPrivate\fresh-usb-ipv6-discovery-private.log"
$taskNeighbors = @(Get-NetNeighbor -InterfaceIndex $taskAdapter.InterfaceIndex -AddressFamily IPv6 | Where-Object { $_.IPAddress -like 'fe80:*' })
if ($taskNeighbors.Count -ne 1) { throw 'Expected one link-local USB peer; inspect inventory before retrying' }
$taskBackup = "$taskPrivate\usb-ipv6-before-refresh-private.json"
if (Test-Path -LiteralPath $taskBackup) { throw 'Refresh already recorded; inspect it before another endpoint write' }
Copy-Item -LiteralPath "$taskPrivate\usb-ipv6-candidates-private.json" -Destination $taskBackup
[pscustomobject]@{
    IPAddress = ($taskNeighbors[0].IPAddress -split '%')[0] + '%' + $taskAdapter.InterfaceIndex
    State = $taskNeighbors[0].State
} | ConvertTo-Json -Compress | Set-Content -LiteralPath "$taskPrivate\usb-ipv6-candidates-private.json"
'Fresh USB endpoint recorded; strict host key and new boot verification still required.'
