param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='passive-r1', [switch]$ProbeLiveness, [switch]$ProbeConsole)
$ErrorActionPreference='Stop'
$taskOut='E:/edk2-samurai-out/kernel366'
$usbipd='C:/Program Files/usbipd-win/usbipd.exe'
if (Test-Path -LiteralPath "$taskOut/$Prefix.json") {throw 'Choose a new output prefix for a new observation'}
$inventory=(& $usbipd list | Out-String)
if (@([regex]::Matches($inventory,'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$')).Count -ne 1) {throw 'Observed EUD endpoint is no longer present/shared'}
$taskKeep=$null
$taskAttached=$false
if ($ProbeLiveness -and $ProbeConsole) {throw 'Select one probe'}
try {
    $taskKeep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','60') -WindowStyle Hidden -PassThru
    & wsl -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; test -r /sys/kernel/debug/usb/usbmon/0u'
    if ($LASTEXITCODE -ne 0) {throw 'Host USB monitor setup failed'}
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed'}
    $taskAttached=$true
    $taskEnumerated=$false
    for ($taskAttempt=0;$taskAttempt -lt 10;$taskAttempt++) {
        & wsl -d Ubuntu -u root -- lsusb -d 05c6:9505
        if ($LASTEXITCODE -eq 0) {$taskEnumerated=$true;break}
        Start-Sleep -Milliseconds 500
    }
    if (!$taskEnumerated) {throw 'EUD did not enumerate in WSL after attach'}
    $taskArguments=@('-d','Ubuntu','-u','root','--','python3','/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py','--seconds','15','--read-size','16','--out',"/mnt/e/edk2-samurai-out/kernel366/$Prefix")
    if ($ProbeLiveness) {$taskArguments+=@('--hex','90 01 15','--repeat','1','--ack','eud: tty byte=15')}
    if ($ProbeConsole) {$taskArguments+=@('--hex','90 01 0a','--repeat','1','--ack','eud: tty byte=0a')}
    & wsl @taskArguments
    if ($LASTEXITCODE -ne 0) {throw 'Passive capture failed; inspect retained output'}
} finally {
    if ($taskAttached) {& $usbipd detach --busid 6-5}
    if ($taskKeep) {
        if (!$taskKeep.HasExited) {$taskKeep.Kill();$taskKeep.WaitForExit()}
        $taskKeep.Dispose()
    }
}
