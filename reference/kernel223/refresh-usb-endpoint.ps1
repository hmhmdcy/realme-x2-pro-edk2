$ErrorActionPreference='Stop'
$taskPrivate='E:/edk2-samurai-out/kernel223'
$taskAdapters=@(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -like 'UsbNcm Host Device*' })
if ($taskAdapters.Count -ne 1) {throw 'No unique active USB NCM interface'}
$taskAdapter=$taskAdapters[0]
$taskPing=& C:/Windows/System32/PING.EXE -6 -n 2 -w 1000 ('ff02::1%'+$taskAdapter.InterfaceIndex)
$taskPing | Set-Content -LiteralPath "$taskPrivate/fresh-usb-ipv6-discovery-private.log"
$taskNeighbors=@(Get-NetNeighbor -InterfaceIndex $taskAdapter.InterfaceIndex -AddressFamily IPv6 | Where-Object {$_.IPAddress -like 'fe80:*' -and $_.State -in @('Reachable','Stale','Delay','Probe')})
if ($taskNeighbors.Count -ne 1) {throw 'No unique scoped USB peer; inspect inventory'}
$taskDest="$taskPrivate/usb-ipv6-candidates-private.json"
if (Test-Path -LiteralPath $taskDest) {throw 'Current discovery already recorded; inspect before changing'}
[pscustomobject]@{IPAddress=($taskNeighbors[0].IPAddress -split '%')[0]+'%'+$taskAdapter.InterfaceIndex;State=$taskNeighbors[0].State} | ConvertTo-Json -Compress | Set-Content -LiteralPath $taskDest
'K223_FRESH_USB_PEER_RECORDED_STRICT_KEY_AND_BOOT_CHECK_PENDING'
