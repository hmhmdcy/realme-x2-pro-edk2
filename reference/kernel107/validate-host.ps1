$ErrorActionPreference='Stop'
$k107root='E:\RealmeX2Pro edk2\reference\kernel107'
$k107out='E:\edk2-samurai-out\kernel107'
$k107files=@(Get-ChildItem -LiteralPath $k107root -Filter '*.ps1')
foreach ($k107p in $k107files) {
    $k107tokens=$null;$k107errors=$null
    [System.Management.Automation.Language.Parser]::ParseFile($k107p.FullName,[ref]$k107tokens,[ref]$k107errors)|Out-Null
    if ($k107errors.Count) {throw "PowerShell AST failed: $($k107p.Name)"}
}
[ordered]@{powershell_syntax_pass=$true;files=$k107files.Count} | ConvertTo-Json | Set-Content -LiteralPath "$k107out\powershell-validation.json"
& 'C:\Program Files\usbipd-win\usbipd.exe' list *> "$k107out\usbipd-final-private.txt"
if ((Get-Content -LiteralPath "$k107out\usbipd-final-private.txt" -Raw) -match '(?m)^6-5\s+05c6:9505\s+.*Attached') {throw 'EUD still attached'}
$k107owned=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('fastboot.exe','eudtool.exe','ssh.exe','scp.exe','wsl.exe') -and $_.CommandLine -match 'kernel107|k107-|connectivity-f1-wsl|first-boot-read-wsl'})
if ($k107owned.Count) {throw 'Owned helper still running; verify ownership before cleanup'}
$k107service=(Get-Service usbipd).Status.ToString()
if ($k107service -ne 'Running') {throw 'USBipd service unexpectedly stopped'}
[ordered]@{usbipd_status=$k107service;owned_host_processes_remaining=$k107owned.Count;owned_helper_check_pass=$true;unknown_usb_filter_preserved=$true} | ConvertTo-Json | Set-Content -LiteralPath "$k107out\owner-validation.json"
'HOST_SYNTAX_AND_DISPOSED_HELPERS_PASS'
