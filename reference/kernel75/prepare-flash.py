from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel74/flash-drain.ps1').read_text().replace('k74','k75').replace('kernel74','kernel75').replace('drain-','gpu-')
s=s.replace('c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7','8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5')
s=s.replace('logdump-k75-drain.img','logdump-k75-gpu.img')
s=s.replace("$hash -ne '8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5'","$hash -ne '7b06c47179147f7a011fcedb038a9f5adc6741a77174feda0ea62c9914c4404e'")
extra='''$fw=Get-Content "$k75out\\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$fw.other_executable_bytes_unchanged -or !$fw.firmware_dtb_raw_section_matches -or !$fw.semantic_dtb_changes.exactly_three_semantic_properties_changed) {throw 'Firmware audit failed'}
if ((Get-FileHash "$k75out\\boot-before.img").Hash.ToLowerInvariant() -ne '57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999') {throw 'Boot rollback hash mismatch'}
$bootimage="$k75out\\boot-k75-gpu.img"
if ((Get-FileHash $bootimage).Hash.ToLowerInvariant() -ne '43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b') {throw 'Boot candidate hash mismatch'}
$bootsize=Invoke-K72Fastboot 'gpu-confirm-size-boot' @('-s','62bc28a1','getvar','partition-size:boot') 15
if ($bootsize -notmatch 'partition-size:boot:\\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -lt (Get-Item $bootimage).Length) {throw 'Boot partition size mismatch'}
'''
s=s.replace("$flash=Invoke-K72Fastboot",extra+"$flash=Invoke-K72Fastboot",1)
s=s.replace("$reboot=Invoke-K72Fastboot",'''$bootflash=Invoke-K72Fastboot 'gpu-flash-boot' @('-s','62bc28a1','flash','boot',$bootimage) 60
if ($bootflash -notmatch "Writing 'boot'\\s+OKAY") {throw 'Boot write not observed'}
$bootflash
$reboot=Invoke-K72Fastboot''',1)
s=s.replace("flashed_partitions=@('logdump')","flashed_partitions=@('logdump','boot')").replace('boot_written=$false','boot_written=$true')
(ref/'flash-gpu.ps1').write_text(s)
print('Flash script is restricted to boot/logdump and checks fresh F1, serial/product/partition sizes, audits and rollback pair.')
