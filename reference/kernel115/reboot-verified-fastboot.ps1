param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='display-recovery')
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel115'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified private device identity required'}
if ((Get-Content -LiteralPath "$out/$Prefix-freeze.out" -Raw) -notmatch 'KERNEL115_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Current root freeze receipt required'}
$events=Get-Content -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'Fresh F1 receipt required'}
foreach ($item in @(@('product',@('-s',$serial,'getvar','product')),@('reboot',@('-s',$serial,'reboot')))) {
    $name=$item[0];$p=$null
    try {
        $p=Start-Process -FilePath $fb -ArgumentList $item[1] -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/$Prefix-fastboot-$name.out" -RedirectStandardError "$out/$Prefix-fastboot-$name.err"
        if (!$p.WaitForExit(15000)) {throw 'Fastboot operation timed out'}
        $p.WaitForExit();if ($p.ExitCode -ne 0) {throw 'Fastboot operation failed'}
        if ($name -eq 'product' -and ((Get-Content -LiteralPath "$out/$Prefix-fastboot-product.err" -Raw)+(Get-Content -LiteralPath "$out/$Prefix-fastboot-product.out" -Raw)) -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
    } finally {if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}}
}
Write-Output 'VERIFIED_FASTBOOT_REBOOT_ONLY_NO_PARTITION_FLASH'
