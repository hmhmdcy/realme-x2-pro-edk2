$ErrorActionPreference = 'Stop'
$savedPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue' # existing hrdevmon warning is not a failed list
    $usb = & 'C:\Program Files\usbipd-win\usbipd.exe' list 2>$null
    $usbExit = $LASTEXITCODE
} finally { $ErrorActionPreference = $savedPreference }
if ($usbExit -ne 0) { throw 'usbipd list failed' }
$files = @(
    'E:\RealmeX2Pro edk2\linux-port\eud.c',
    'E:\RealmeX2Pro edk2\linux-port\scripts\eud-terminal.ps1',
    'E:\eud-host\eud-terminal.ps1',
    'E:\edk2-samurai-out\logdump-rx48-tx-journal.img',
    'C:\Windows\System32\drivers\qcusbser.sys'
)
$state = [ordered]@{
    captured_at = (Get-Date).ToString('o')
    image = 'logdump-rx48-tx-journal.img'
    flash_this_round = $false
    reboot_this_round = $false
    serial_closed = $true
    new_admin_capture = $false
    installed_terminal_modified = $false
    devices = @(Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPDeviceID -match 'VID_05C6&PID_950[015]' } | Select-Object Name,Status,PNPDeviceID)
    ports = @([IO.Ports.SerialPort]::GetPortNames())
    target_usbipd = @($usb | Where-Object { $_ -match '05c6:950[15]' })
    hashes = @(Get-FileHash -LiteralPath $files | Select-Object Path,Hash)
    known_eud_helpers = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(powershell|python|python3|wsl)\.exe$' -and
        $_.CommandLine -match '(eud-terminal|eud-step|eud-usb-session)'
    } | Select-Object ProcessId,Name)
}
$state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'final-state.json') -Encoding UTF8
$state | ConvertTo-Json -Depth 5
