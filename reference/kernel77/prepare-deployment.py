"""Create a boot-only deployment script from the verified candidate."""
from pathlib import Path
import hashlib,json
ref=Path(__file__).resolve().parent; out=Path('/mnt/e/edk2-samurai-out/kernel77')
firmware=json.loads((out/'firmware-validation.json').read_text())
candidate=json.loads((out/'candidate-validation.json').read_text())
assert firmware['firmware_dtb_raw_section_matches'] and firmware['other_executable_bytes_unchanged']
assert candidate['only_boot_update_required'] and candidate['kernel_image_config_and_logdump_unchanged']
boot_hash=hashlib.sha256((out/'boot-k77-gauge.img').read_bytes()).hexdigest()
assert boot_hash==firmware['boot_after_sha256']
script=(ref.parent/'kernel75/flash-final.ps1').read_text().replace('kernel75','kernel77').replace('k75','k77').replace('final-','gauge-')
start=script.index('$audit=')
end=script.index('$events=',start)
checks='''$audit=Get-Content "$k77out\\candidate-validation.json" -Raw | ConvertFrom-Json
$fw=Get-Content "$k77out\\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$audit.only_boot_update_required -or !$audit.kernel_image_config_and_logdump_unchanged -or !$audit.dtb_audit.only_i2c15_status_frequency_and_gauge_added -or !$fw.other_executable_bytes_unchanged -or !$fw.firmware_dtb_raw_section_matches) {throw 'Candidate audit failed'}
if ((Get-FileHash "$k77out\\boot-before.img").Hash.ToLowerInvariant() -ne '43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b') {throw 'Boot rollback mismatch'}
if ((Get-FileHash "$k77out\\logdump-before.img").Hash.ToLowerInvariant() -ne '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0') {throw 'Logdump baseline mismatch'}
'''
script=script[:start]+checks+script[end:]
script=script.replace('partition-size:logdump','partition-size:boot').replace('gauge-confirm-size-logdump','gauge-confirm-size-boot')
script=script.replace('logdump-k77-final.img','boot-k77-gauge.img')
script=script.replace("if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0')",f"if ($partitionBytes -lt (Get-Item $image).Length -or $hash -ne '{boot_hash}')")
script=script.replace('gauge-flash-logdump','gauge-flash-boot').replace("'flash','logdump'","'flash','boot'").replace("Writing 'logdump'","Writing 'boot'")
script=script.replace("flashed_partitions=@('logdump')","flashed_partitions=@('boot')").replace('boot_written=$false','boot_written=$true')
script=script.replace('boot_written=$true;','boot_written=$true;logdump_written=$false;')
assert 'flash\',\'logdump' not in script and 'boot-k77-gauge.img' in script
(ref/'flash-gauge.ps1').write_text(script)
s=(ref.parent/'kernel75/reboot-f1.ps1').read_text().replace('kernel75','kernel77').replace("$Prefix='display'","$Prefix='gauge'")
(ref/'reboot-f1.ps1').write_text(s)
print('Boot-only deployment prepared:',boot_hash)
