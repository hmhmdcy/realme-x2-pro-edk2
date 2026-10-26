$ErrorActionPreference = 'Stop'
$fb = 'C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$root = 'E:\edk2-samurai-out\kernel66'
$image = 'E:\edk2-samurai-out\logdump-k66-map.img'
function Invoke-K66Fastboot([string]$Name, [string[]]$Arguments, [int]$TimeoutSeconds) {
    $proc = $null
    try {
        $proc = Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$root\$Name.out" -RedirectStandardError "$root\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds * 1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content -LiteralPath "$root\$Name.out" -Raw) + (Get-Content -LiteralPath "$root\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$devices = Invoke-K66Fastboot 'map-confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') { throw 'Expected phone not independently enumerated in fastboot' }
$product = Invoke-K66Fastboot 'map-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') { throw 'Unexpected product' }
if ((Get-Item -LiteralPath $image).Length -ne 67108864) { throw 'Unexpected image length' }
if ((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d') { throw 'Image hash mismatch' }
$flash = Invoke-K66Fastboot 'map-flash' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") { throw 'No successful logdump write evidence' }
$reboot = Invoke-K66Fastboot 'map-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';partition='logdump';image_sha256='c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d';flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content -LiteralPath "$root\map-flash-validation.json"
$flash
$reboot
