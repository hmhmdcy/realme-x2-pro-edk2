$ErrorActionPreference='Stop'
$captureRoot='E:\edk2-samurai-out\rx54'
$devices=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_950*' } | Select-Object Status,FriendlyName,InstanceId)
$owners=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'eud-terminal\.ps1|eud-console-overlap\.ps1|eud-usb-(overlap|repeated-console|console-f1).*\.py' -and $_.ProcessId -ne $PID } | Select-Object ProcessId,Name,CommandLine)
$usbipdReply=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'usbipd state failed' }
$target=@($usbipdReply -split "`r?`n" | Where-Object { $_ -match '05c6:950[15]' })
if ($devices.Count -ne 3 -or @($devices | Where-Object Status -ne 'OK').Count -or $owners.Count -or $target.Count -ne 2 -or ($target -join "`n") -match 'Attached') { throw 'Final device/ownership check failed' }
$paths=@('E:\RealmeX2Pro edk2\linux-port\eud.c','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')
$hashes=@($paths | ForEach-Object { Get-FileHash -LiteralPath $_ -Algorithm SHA256 | Select-Object Path,Hash })
$linuxHashes=@(wsl -d Ubuntu -- sha256sum /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c /home/cy122/x2pro-linux/linux/arch/arm64/boot/Image)
if ($LASTEXITCODE -ne 0) { throw 'Linux source hashes failed' }
$state=@{utc=(Get-Date).ToUniversalTime().ToString('o'); devices=$devices; known_eud_helpers=$owners; ports=[IO.Ports.SerialPort]::GetPortNames(); target_usbipd=$target; hashes=$hashes; linux_hashes=$linuxHashes; serial_closed=$true; usb_owners_closed=$true; usb_detached_or_removed_after_f1=$true; flashed_partitions=@(); flash_count=0; same_candidate_reboots=1; installed_terminal_modified=$false; new_windows_admin_capture=$false; restored_native='restored-native'; hardware_failures_unresolved='RX53 seq7287 TX gap remains open; this regression is not a TX fix'}
[IO.File]::WriteAllText("$captureRoot\final-state.json",($state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output 'All three EUD nodes OK; no known owner; COM14 closed by terminal finally; Shared/not Attached; no flash.'
