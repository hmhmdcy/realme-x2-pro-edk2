from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126'
code=(r/'reference/kernel119/enable-eud.ps1').read_text().replace('kernel119','kernel126').replace('KERNEL119','K126').replace("'sensor-power-first'","'tpg-first'");(ref/'enable-eud.ps1').write_text(code)
code=(r/'reference/kernel119/enter-bootloader.ps1').read_text().replace('kernel119','kernel126').replace('k119','k126').replace('KERNEL119','K126').replace("'sensor-power-first'","'tpg-first'")
code=code.replace('$proc=$null;$keep=$null','$proc=$null;$keep=$null;$frozen=$false;$receipt=$false')
code=code.replace("Write-Output 'FROZEN_ROOT_F1_BOOTLOADER_RECEIPT_CONFIRMED'","$receipt=$true\n    Write-Output 'FROZEN_ROOT_F1_BOOTLOADER_RECEIPT_CONFIRMED'")
code=code.replace('} finally {\n    &',"} finally {\n    if ($frozen -and !$receipt) {\n        try {\n            $thaw=& 'E:/RealmeX2Pro edk2/reference/kernel109/usb-ssh-pmos.ps1' -Command \"test `\"`$(cat /proc/sys/kernel/random/boot_id)`\" = '$bootId' && fsfreeze -u / && echo K126_CONTROLLED_THAW\"\n            $thaw | Set-Content -LiteralPath \"$out\\$Prefix-thaw-private.txt\" -Encoding utf8NoBOM\n        } catch { $_ | Out-String | Set-Content -LiteralPath \"$out\\$Prefix-thaw-error-private.txt\" -Encoding utf8NoBOM }\n    }\n    &")
(ref/'enter-bootloader.ps1').write_text(code)
print('K126_FRESH_BOOT_FLYWHEEL_WITH_PRE_FREEZE_USBMON_AND_SINGLE_F1_READY')
