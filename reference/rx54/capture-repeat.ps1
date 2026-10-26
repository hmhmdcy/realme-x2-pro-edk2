$ErrorActionPreference = 'Stop'
$captureRoot = 'E:\edk2-samurai-out\rx54'
$usbipd = 'C:\Program Files\usbipd-win\usbipd.exe'
$present = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_950*' } | Select-Object Status,FriendlyName,InstanceId)
if ($present.Count -ne 3 -or @($present | Where-Object Status -ne 'OK').Count) { throw 'EUD nodes not all OK' }
$owners = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'eud-terminal\.ps1|eud-console-overlap\.ps1|eud-usb-overlap.*\.py|eud-usb-repeated-console\.py' -and $_.ProcessId -ne $PID } | Select-Object ProcessId,Name,CommandLine)
if ($owners.Count) { throw 'Existing EUD owner; inspect before proceeding' }
$currentHelper = (Get-FileHash -LiteralPath "$captureRoot\eud-usb-repeated-console.py" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($currentHelper -ne '48bad103de1b41705d194ad332d88038807f3724753379af3d233d6fc6fa74ce') { throw 'Helper changed after review' }
@{utc=(Get-Date).ToUniversalTime().ToString('o'); nodes=$present; owners=$owners; ports=[IO.Ports.SerialPort]::GetPortNames(); helper_sha256=$currentHelper; no_flash=$true} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$captureRoot\before-state.json" -Encoding UTF8
wsl -d Ubuntu -u root -- true
if ($LASTEXITCODE -ne 0) { throw 'WSL unavailable' }
$attached = $false
try {
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $usbipd attach --wsl --busid 6-5
        $attachCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    if ($attachCode -ne 0) { throw "USB attach failed: $attachCode" }
    $attached = $true
    wsl -d Ubuntu -u root -- bash /mnt/e/edk2-samurai-out/rx54/bootstrap-repeat.sh
    $captureCode = $LASTEXITCODE
    if ($captureCode -ne 0) { throw "Capture exited: $captureCode" }
} finally {
    if ($attached) {
        $savedPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & $usbipd detach --busid 6-5
        } finally { $ErrorActionPreference = $savedPreference }
    }
    Write-Host 'USB owner finished; detach attempted in finally.'
}
