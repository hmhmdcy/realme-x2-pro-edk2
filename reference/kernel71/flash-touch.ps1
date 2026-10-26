$ErrorActionPreference='Stop'
$k71fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k71root='E:\edk2-samurai-out\kernel71'
function Invoke-K71Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $k71proc=$null
    try {
        if (Test-Path -LiteralPath "$k71root\$Name.out") { throw 'Use a new output prefix' }
        $k71proc=Start-Process -FilePath $k71fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k71root\$Name.out" -RedirectStandardError "$k71root\$Name.err"
        if (!$k71proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $k71proc.WaitForExit()
        if ($k71proc.ExitCode -ne 0) { throw "$Name exit $($k71proc.ExitCode)" }
        return ((Get-Content -LiteralPath "$k71root\$Name.out" -Raw)+(Get-Content -LiteralPath "$k71root\$Name.err" -Raw))
    } finally {
        if ($k71proc) {
            if (!$k71proc.HasExited) { $k71proc.Kill();$k71proc.WaitForExit() }
            $k71proc.Dispose()
        }
    }
}
$k71baseline=Get-Content -LiteralPath "$k71root\baseline-bootmeta.validated.txt" -Raw
if ($k71baseline -notmatch '(?m)^PARTNAME=boot$' -or $k71baseline -notmatch '(?m)^6682624 /tmp/K71B/boot-prefix$' -or $k71baseline -notmatch '785071a405d839b13d3d0ef040f42d227b09659e6dd0d3df96bb3689ced0635b') { throw 'Unverified rollback baseline' }
$k71audit=Get-Content -LiteralPath "$k71root\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$k71audit.other_executable_bytes_unchanged -or !$k71audit.semantic_dtb_changes.all_other_properties_unchanged -or !$k71audit.compat_append_unchanged) { throw 'Firmware audit incomplete' }
$k71f1events=Get-Content -LiteralPath "$k71root\touch-f1-wsl.events.jsonl" | ForEach-Object { $_ | ConvertFrom-Json }
if (!@($k71f1events | Where-Object { $_.event -eq 'receipt' -and $_.text -eq 'F1' }).Count) { throw 'No fresh F1 receipt' }
$k71usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($k71usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') { throw 'EUD still attached' }
$k71devices=Invoke-K71Fastboot 'confirm-devices' @('devices') 15
if ($k71devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') { throw 'Phone not independently enumerated in fastboot' }
$k71product=Invoke-K71Fastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($k71product -notmatch 'product:\s*msmnile') { throw 'Unexpected product' }
$k71items=@(
    @{Partition='boot';File='boot-k71-touch.img';Length=6680576;Hash='a4f4b75a52ec13a9b0b5cd4ebd678daa9a9dafd36548ce82ce4602a1fbcc15db'},
    @{Partition='logdump';File='logdump-k71-touch.img';Length=67108864;Hash='f6837573c908eddad7a2d8d0ab494c259ff99a9a5b85878e3b6747d40b2d3fb8'}
)
foreach ($k71item in $k71items) {
    $k71size=Invoke-K71Fastboot ('confirm-size-'+$k71item.Partition) @('-s','62bc28a1','getvar',('partition-size:'+$k71item.Partition)) 15
    if ($k71size -notmatch ('partition-size:'+$k71item.Partition+':\s*(0x[0-9a-fA-F]+)')) { throw 'Partition size unavailable' }
    $k71partSize=[Convert]::ToInt64($Matches[1].Substring(2),16)
    $k71image=Join-Path $k71root $k71item.File
    if ((Get-Item -LiteralPath $k71image).Length -ne $k71item.Length -or $k71partSize -lt $k71item.Length) { throw 'Image or partition length mismatch' }
    if ((Get-FileHash -LiteralPath $k71image).Hash.ToLowerInvariant() -ne $k71item.Hash) { throw 'Image hash mismatch' }
    $k71item.PartitionLength=$k71partSize
}
foreach ($k71item in $k71items) {
    $k71flash=Invoke-K71Fastboot ('flash-'+$k71item.Partition) @('-s','62bc28a1','flash',$k71item.Partition,(Join-Path $k71root $k71item.File)) 60
    if ($k71flash -notmatch ("Writing '"+$k71item.Partition+"'\s+OKAY")) { throw 'No successful write evidence' }
    $k71flash
}
$k71reboot=Invoke-K71Fastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';images=$k71items;flash_success=$true;reboot_success=$true;processes_disposed=$true;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$k71root\flash-validation.json"
$k71reboot
