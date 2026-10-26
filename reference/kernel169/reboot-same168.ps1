$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel169'
$prefix='same168-second-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$events=Get-Content -LiteralPath "$out/$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition missing'}
$deviceLog="$out/bootloader-devices-private.txt"
if (Test-Path -LiteralPath $deviceLog) {throw 'Fresh bootloader operation required'}
& $fb devices *> $deviceLog
if ($LASTEXITCODE -ne 0 -or (Get-Content -Raw -LiteralPath $deviceLog) -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Current bootloader identity mismatch'}
& $fb -s $serial getvar product *> "$out/bootloader-product-private.txt"
if ($LASTEXITCODE -ne 0 -or (Get-Content -Raw -LiteralPath "$out/bootloader-product-private.txt") -notmatch 'product:\s*msmnile') {throw 'Current product mismatch'}
& $fb -s $serial reboot *> "$out/reboot-private.log"
if ($LASTEXITCODE -ne 0) {throw 'Reboot failed; inspect state before retrying'}
Write-Output 'K169_SAME_KERNEL168_REBOOT_ACCEPTED_WITHOUT_FLASH'
