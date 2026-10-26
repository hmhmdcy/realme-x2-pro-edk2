$ErrorActionPreference='Stop'
$k68fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k68root='E:\edk2-samurai-out\kernel68'
$k68image="$k68root\boot-k68-opp.img"
function Invoke-K68Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $k68proc=$null
    try {
        if (Test-Path -LiteralPath "$k68root\$Name.out") { throw 'Use a new output prefix' }
        $k68proc=Start-Process -FilePath $k68fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k68root\$Name.out" -RedirectStandardError "$k68root\$Name.err"
        if (!$k68proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $k68proc.WaitForExit()
        if ($k68proc.ExitCode -ne 0) { throw "$Name exit $($k68proc.ExitCode)" }
        return ((Get-Content -LiteralPath "$k68root\$Name.out" -Raw)+(Get-Content -LiteralPath "$k68root\$Name.err" -Raw))
    } finally {
        if ($k68proc) {
            if (!$k68proc.HasExited) { $k68proc.Kill();$k68proc.WaitForExit() }
            $k68proc.Dispose()
        }
    }
}
$k68baseline=Get-Content -LiteralPath "$k68root\baseline-bootmeta.validated.txt" -Raw
if ($k68baseline -notmatch '(?m)^6678528 /tmp/K68B/boot-prefix$' -or $k68baseline -notmatch '8c9dea12a8eca687f9da59e067da8c3dfb91bec4d61ae3371c67292d434c7edd') { throw 'Unverified rollback baseline' }
$k68audit=Get-Content -LiteralPath "$k68root\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$k68audit.other_executable_bytes_unchanged -or $k68audit.sole_semantic_dtb_change -ne '/opp-table-cpu7/opp-2956800000') { throw 'Firmware audit incomplete' }
$k68events=Get-Content -LiteralPath "$k68root\opp-f1.events.jsonl" | ForEach-Object { $_ | ConvertFrom-Json }
if (!@($k68events | Where-Object { $_.event -eq 'receipt' -and $_.text -eq 'F1' }).Count) { throw 'No fresh F1 receipt' }
$k68usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($k68usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') { throw 'EUD still attached' }
$k68devices=Invoke-K68Fastboot 'boot-confirm-devices' @('devices') 15
if ($k68devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') { throw 'Phone not independently enumerated in fastboot' }
$k68product=Invoke-K68Fastboot 'boot-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($k68product -notmatch 'product:\s*msmnile') { throw 'Unexpected product' }
$k68size=Invoke-K68Fastboot 'boot-confirm-size' @('-s','62bc28a1','getvar','partition-size:boot') 15
if ($k68size -notmatch 'partition-size:boot:\s*(0x[0-9a-fA-F]+)') { throw 'Boot partition size unavailable' }
$k68partSize=[Convert]::ToInt64($Matches[1].Substring(2),16)
if ((Get-Item -LiteralPath $k68image).Length -ne 6682624 -or $k68partSize -lt 6682624) { throw 'Image or partition length mismatch' }
if ((Get-FileHash -LiteralPath $k68image).Hash.ToLowerInvariant() -ne '785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b') { throw 'Image hash mismatch' }
$k68flash=Invoke-K68Fastboot 'boot-flash' @('-s','62bc28a1','flash','boot',$k68image) 60
if ($k68flash -notmatch "Writing 'boot'\s+OKAY") { throw 'No successful boot write evidence' }
$k68reboot=Invoke-K68Fastboot 'boot-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';partition='boot';partition_bytes=$k68partSize;image_bytes=6682624;image_sha256='785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b';flash_success=$true;reboot_success=$true;processes_disposed=$true;logdump_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json | Set-Content -LiteralPath "$k68root\boot-flash-validation.json"
$k68flash
$k68reboot
