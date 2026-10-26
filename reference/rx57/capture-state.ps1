param([string]$Output='state-after-attempt-01.json')
$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx57'
if($Output -notmatch '^[-a-z0-9]+\.json$'){throw 'Local output name only.'}
$rxInstance='USB\VID_05C6&PID_9505\8&5580DC5&0&5'
$rxDevices=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB\VID_05C6&PID_950*'} | Select-Object Status,FriendlyName,InstanceId,ConfigManagerErrorCode)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|rx57[\\/]capture-windows(?:-02)?\.ps1'} | Select-Object ProcessId,Name,CommandLine)
$rxUsbipd=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP read failed.'}
$rxTarget=@($rxUsbipd -split "`r?`n" | Where-Object {$_ -match '05c6:950[15]'})
$rxReg=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008',$false)
try{
 $rxValues=@(foreach($rxName in @('QCDriverConfig','QCDriverLoggingDirectory')){[pscustomobject]@{name=$rxName;present=(@($rxReg.GetValueNames()) -contains $rxName);value=$rxReg.GetValue($rxName,$null)}})
}finally{$rxReg.Dispose()}
$rxPaths=@('E:\RealmeX2Pro edk2\linux-port\eud.c','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img','C:\Windows\System32\drivers\qcusbser.sys','C:\Windows\System32\WindowsPowerShell\v1.0\Modules\PnpDevice\PnpDevice.cdxml')
$rxHashes=@($rxPaths | ForEach-Object {Get-FileHash -LiteralPath $_ | Select-Object Path,Hash})
$rxLinux=@(wsl -d Ubuntu -- sha256sum /home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c /home/cy122/x2pro-linux/linux/arch/arm64/boot/Image)
if($LASTEXITCODE -ne 0){throw 'Linux identity read failed.'}
$rxHelperStates=@(foreach($rxAttempt in @('01','02')){
 $rxStatusPath=Join-Path $rxRoot ('control-'+$rxAttempt+'\status.json')
 if(Test-Path -LiteralPath $rxStatusPath){
  $rxStatus=Get-Content -Raw -LiteralPath $rxStatusPath | ConvertFrom-Json
  [pscustomobject]@{attempt=$rxAttempt;status=$rxStatus;process_alive=($null -ne (Get-Process -Id $rxStatus.pid -ErrorAction SilentlyContinue))}
 }
})
$rxLogs=@(foreach($rxAttempt in @('01','02')){Get-ChildItem -LiteralPath (Join-Path $rxRoot ('driver-logs-'+$rxAttempt)) -File -ErrorAction SilentlyContinue | ForEach-Object {[pscustomobject]@{attempt=$rxAttempt;name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}}})
$rxState=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o');snapshot_read_only=$true;device_instance=$rxInstance;devices=$rxDevices;known_serial_owners=$rxOwners;target_usbipd=$rxTarget;registry_values=$rxValues;helper_states=$rxHelperStates;driver_logs=$rxLogs;hashes=$rxHashes;linux_hashes=$rxLinux;port_opened_by_this_state_helper=$false;phone_flash_count=0;phone_reboot_count=0;driver_install_count=0;installed_terminal_modified=$false;fresh_linux_receipt_measured_by_this_helper=$false}
if($rxDevices.Count -ne 3 -or @($rxDevices | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or @($rxValues | Where-Object present).Count -or ($rxTarget -join "`n") -match 'Attached' -or @($rxHelperStates | Where-Object process_alive).Count){throw 'Final restored state verification failed.'}
[IO.File]::WriteAllText((Join-Path $rxRoot $Output),($rxState | ConvertTo-Json -Depth 9).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
[pscustomobject]@{output=$Output;nodes_ok=3;logging_values_absent=$true;known_serial_owners=$rxOwners.Count;helpers_exited=$true;driver_log_files=$rxLogs.Count} | ConvertTo-Json
