$ErrorActionPreference='Stop'
$taskPrivate='E:/edk2-samurai-out/kernel214'
$taskFile="$taskPrivate/fresh-usb-peers-private.json"
if (Test-Path -LiteralPath $taskFile) {throw 'Discovery already recorded; inspect its evidence before another attempt'}
$taskAdapters=@(Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -like 'UsbNcm Host Device*' })
$taskPeers=@()
foreach ($taskAdapter in $taskAdapters) {
    $taskPing=& C:/Windows/System32/PING.EXE -6 -n 2 -w 1000 ('ff02::1%'+$taskAdapter.InterfaceIndex)
    $taskPing | Set-Content -LiteralPath "$taskPrivate/fresh-usb-discovery-private.log"
    $taskNeighbors=@(Get-NetNeighbor -InterfaceIndex $taskAdapter.InterfaceIndex -AddressFamily IPv6 | Where-Object {$_.IPAddress -like 'fe80:*' -and $_.State -in @('Reachable','Stale','Delay','Probe')})
    foreach ($taskNeighbor in $taskNeighbors) {
        $taskPeers+=@{IPAddress=($taskNeighbor.IPAddress -split '%')[0]+'%'+$taskAdapter.InterfaceIndex;State=[string]$taskNeighbor.State}
    }
}
@{ActiveUsbAdapters=$taskAdapters.Count;Peers=$taskPeers} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $taskFile
@{ActiveUsbAdapters=$taskAdapters.Count;ScopedCandidateCount=$taskPeers.Count;ReadOnlyDiscovery=$true} | ConvertTo-Json -Compress
