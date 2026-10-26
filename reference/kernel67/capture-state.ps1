param([string]$Name='opp-finish-state', [string]$Image='E:\edk2-samurai-out\logdump-k67-opp.img', [string]$Kernel='#59', [string]$BootId='83952af2-74ee-4dad-9e01-16ee951d4c20', [int]$Flashes=1)
$ErrorActionPreference='Stop'
$k67root='E:\edk2-samurai-out\kernel67'
$k67before=Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel66\baseline-state.json' -Raw | ConvertFrom-Json
$k67nodes=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k67nodes.Count -ne 3 -or @($k67nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k67target=@($k67nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k67key=(Get-PnpDeviceProperty -InstanceId $k67target -KeyName DEVPKEY_Device_Driver).Data
$k67props=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k67key)
$k67owners=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k67linuxOwners=(& 'C:\Windows\System32\wsl.exe' -d Ubuntu -- bash -c "ps -eo pid,ppid,args | grep -E '[p]ython3 .*/eud-usb|[e]ud-terminal|[e]udtool' || true" | Out-String).Trim()
$k67usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k67usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k67owners.Count -or $k67linuxOwners) { throw 'Expected released, unattached USB target' }
$k67hashes=[ordered]@{}
foreach ($k67prop in $k67before.hashes.PSObject.Properties) {
    $k67hashes[$k67prop.Name]=(Get-FileHash -LiteralPath $k67prop.Name).Hash.ToLowerInvariant()
    if ($k67hashes[$k67prop.Name] -ne $k67prop.Value) { throw "Original file changed: $($k67prop.Name)" }
}
$k67loggingAbsent=(!$k67props.PSObject.Properties['QCDriverConfig'] -and !$k67props.PSObject.Properties['QCDriverLoggingDirectory'])
$k67traces=(& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k67traceActive=$k67traces -match 'EUD-RX(?:5[7-9]|6[0-7])'
if (!$k67loggingAbsent -or $k67traceActive -or $k67props.InfPath -ne 'oem102.inf' -or $k67props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k67state=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase=$Name;nodes=$k67nodes;known_owners=$k67owners;known_linux_owners=$k67linuxOwners;usbipd=$k67usb;hashes=$k67hashes;driver_inf=$k67props.InfPath;driver_version=$k67props.DriverVersion;temporary_logging_absent=$k67loggingAbsent;active_eud_trace=$k67traceActive;flashed_partitions=@('logdump')*$Flashes;boot_written=$false;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel=$Kernel;last_confirmed_boot_id=$BootId;live_logdump_sha256=(Get-FileHash -LiteralPath $Image).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText("$k67root\$Name.json",($k67state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output "Saved ${Name}: COM14 Shared/unattached; three nodes OK; no known owners; original files unchanged."
