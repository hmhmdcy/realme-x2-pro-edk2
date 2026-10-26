$ErrorActionPreference='Stop'
$root='E:\edk2-samurai-out\rx55'
$devices=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_950*' } | Select-Object Status,FriendlyName,InstanceId)
$owners=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1' -and $_.ProcessId -ne $PID } | Select-Object ProcessId,Name,CommandLine)
$usbipd=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'usbipd state failed' }
$target=@($usbipd -split "`r?`n" | Where-Object { $_ -match '05c6:950[15]' })
if ($devices.Count -ne 3 -or @($devices | Where-Object Status -ne 'OK').Count -or $owners.Count -or $target.Count -ne 2 -or ($target -join "`n") -match 'Attached') { throw 'Final device/owner check failed' }
$paths=@('E:\RealmeX2Pro edk2\linux-port\eud.c','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')
$hashes=@($paths | ForEach-Object { Get-FileHash -LiteralPath $_ | Select-Object Path,Hash })
$linux=@(wsl -d Ubuntu -- sha256sum /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c /home/cy122/x2pro-linux/linux/arch/arm64/boot/Image)
if ($LASTEXITCODE -ne 0) { throw 'Linux hashes failed' }
$last=Get-Content -LiteralPath (Join-Path $root 'windows-perf-01.rx-audit.jsonl') -Tail 1 | ConvertFrom-Json
if ($last.event -ne 'closed' -or $last.serial_is_open -or $last.retained_pending_perf -or !$last.perf_probe_disposed -or !$last.probe_detached) { throw 'Missing serial/probe finally closure' }
$state=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o'); devices=$devices; known_eud_helpers=$owners; ports=[IO.Ports.SerialPort]::GetPortNames(); target_usbipd=$target; hashes=$hashes; linux_hashes=$linux; serial_closed=$true; diagnostic_finally_verified=$true; usb_not_attached=$true; flash_count=0; flashed_partitions=@(); same_candidate_reboots=0; installed_terminal_modified=$false; new_windows_admin_capture=$false; kernel_candidate='RX53 console boundary'; unresolved='TX seq7376 absent before accepted-buffer count; first of two startup Ctrl-U writes not accepted; no fix this session'}
[IO.File]::WriteAllText((Join-Path $root 'final-state.json'),($state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
'Three nodes OK; diagnostic finally closed COM14; no owner/attachment; zero flash/reboot; same candidate/installed terminal.'
