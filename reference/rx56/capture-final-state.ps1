$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx56'
$rxDevices=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_950*' } | Select-Object Status,FriendlyName,InstanceId)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1' -and $_.ProcessId -ne $PID } | Select-Object ProcessId,Name,CommandLine)
$rxUsbipd=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'usbipd state failed' }
$rxTarget=@($rxUsbipd -split "`r?`n" | Where-Object { $_ -match '05c6:950[15]' })
if ($rxDevices.Count -ne 3 -or @($rxDevices | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or $rxTarget.Count -ne 2 -or ($rxTarget -join "`n") -match 'Attached') { throw 'Device/owner check failed' }
$rxPaths=@('E:\RealmeX2Pro edk2\linux-port\eud.c','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')
$rxHashes=@($rxPaths | ForEach-Object { Get-FileHash -LiteralPath $_ | Select-Object Path,Hash })
$rxLinux=@(wsl -d Ubuntu -- sha256sum /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c /home/cy122/x2pro-linux/linux/arch/arm64/boot/Image)
if ($LASTEXITCODE -ne 0) { throw 'Linux hashes failed' }
$rxState=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o');devices=$rxDevices;known_eud_helpers=$rxOwners;ports=[IO.Ports.SerialPort]::GetPortNames();target_usbipd=$rxTarget;hashes=$rxHashes;linux_hashes=$rxLinux;no_port_opened_this_session=$true;no_usbip_attach_this_session=$true;flash_count=0;same_candidate_reboots=0;new_windows_admin_capture=$false;registry_changed=$false;installed_terminal_modified=$false;unresolved='RX55 TX seq7376 and startup missing receipt remain; RX56 source/research audit is not a repair.'}
[IO.File]::WriteAllText((Join-Path $rxRoot 'final-state.json'),($rxState | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
'RX56 read-only: three nodes OK, no known owner, Shared/not Attached; candidate and terminal unchanged.'
