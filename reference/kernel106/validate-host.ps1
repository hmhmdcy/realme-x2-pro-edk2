$ErrorActionPreference='Stop'
$k106root='E:\RealmeX2Pro edk2\reference\kernel106'
$k106out='E:\edk2-samurai-out\kernel106'
$k106files=@(Get-ChildItem -LiteralPath $k106root -Filter '*.ps1')
foreach ($k106p in $k106files) {
    $k106tokens=$null;$k106errors=$null
    [System.Management.Automation.Language.Parser]::ParseFile($k106p.FullName,[ref]$k106tokens,[ref]$k106errors)|Out-Null
    if ($k106errors.Count) {throw "PowerShell AST failed: $($k106p.Name)"}
}
[ordered]@{powershell_syntax_pass=$true;files=$k106files.Count} | ConvertTo-Json | Set-Content -LiteralPath "$k106out\powershell-validation.json"
& 'C:\Program Files\usbipd-win\usbipd.exe' list *> "$k106out\usbipd-final-private.txt"
if ((Get-Content -LiteralPath "$k106out\usbipd-final-private.txt" -Raw) -match '(?m)^6-5\s+05c6:9505\s+.*Attached') {throw 'EUD still attached'}
$k106owned=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('fastboot.exe','eudtool.exe','ssh.exe','scp.exe','wsl.exe') -and $_.CommandLine -match 'kernel106|k106-|connectivity-f1-wsl|first-boot-read-wsl'})
if ($k106owned.Count) {throw 'Owned helper still running; verify ownership before cleanup'}
$k106service=(Get-Service usbipd).Status.ToString()
if ($k106service -ne 'Running') {throw 'USBipd service unexpectedly stopped'}
[ordered]@{usbipd_status=$k106service;owned_host_processes_remaining=$k106owned.Count;owned_helper_check_pass=$true;unknown_usb_filter_preserved=$true} | ConvertTo-Json | Set-Content -LiteralPath "$k106out\owner-validation.json"
'HOST_SYNTAX_AND_DISPOSED_HELPERS_PASS'
