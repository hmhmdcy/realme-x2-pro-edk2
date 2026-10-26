$ErrorActionPreference='Stop'
$captureRoot='E:\edk2-samurai-out\rx54'
$fastboot='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$utf8=[Text.UTF8Encoding]::new($false)
$devices=(& $fastboot devices | Out-String)
if ($LASTEXITCODE -ne 0 -or $devices.Trim() -notmatch '^62bc28a1\s+fastboot$') { throw 'Unexpected fastboot device' }
$savedPreference=$ErrorActionPreference
try {
    $ErrorActionPreference='Continue'
    $product=(& $fastboot -s 62bc28a1 getvar product 2>&1 | Out-String)
    $productCode=$LASTEXITCODE
} finally { $ErrorActionPreference=$savedPreference }
if ($productCode -ne 0 -or $product -notmatch 'product: msmnile') { throw 'Unexpected fastboot product' }
[IO.File]::WriteAllText("$captureRoot\f1-fastboot.txt",($devices+$product).Replace("`r`n","`n"),$utf8)
$savedPreference=$ErrorActionPreference
try {
    $ErrorActionPreference='Continue'
    $reply=(& $fastboot -s 62bc28a1 reboot 2>&1 | Out-String)
    $rebootCode=$LASTEXITCODE
} finally { $ErrorActionPreference=$savedPreference }
[IO.File]::WriteAllText("$captureRoot\same-image-reboot.txt",$reply.Replace("`r`n","`n"),$utf8)
if ($rebootCode -ne 0) { throw 'Reboot failed' }
Write-Output 'Rebooted same RX53 logdump; no flash.'
$deadline=(Get-Date).AddSeconds(45)
do {
    $control=@(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_9501\*' -and $_.Status -eq 'OK' })
    if ($control.Count -eq 1) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)
if ($control.Count -ne 1) { throw 'No unique EUD control node' }
& 'E:\eud-host\eudtool.exe' com-up
if ($LASTEXITCODE -ne 0) { throw 'com-up failed' }
$deadline=(Get-Date).AddSeconds(15)
do {
    $ports=@(Get-PnpDevice -PresentOnly -Class Ports -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match '9505.*\(COM\d+\)' -and $_.Status -eq 'OK' })
    if ($ports.Count -eq 1) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)
if ($ports.Count -ne 1) { throw 'No unique EUD COM port' }
$port=[regex]::Match($ports[0].FriendlyName,'COM\d+').Value
& "$captureRoot\passive-serial.ps1" -Port $port -Seconds 50 -Out "$captureRoot\same-image-boot"
