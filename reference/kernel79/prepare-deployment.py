"""Produce the boot-only deployment from verified exact bus-only evidence."""
from pathlib import Path
import hashlib
import json

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel79')
candidate = json.loads((out/'candidate-validation.json').read_text())
firmware = json.loads((out/'firmware-validation.json').read_text())
assert candidate['dtb_audit']['only_gpi0_qup0_i2c1_enabled_and_400khz']
assert candidate['dtb_audit']['no_new_nodes_or_clients']
assert candidate['kernel_image_config_and_logdump_unchanged']
assert firmware['other_executable_bytes_unchanged'] and firmware['firmware_dtb_raw_section_matches']
boot_hash = hashlib.sha256((out/'boot-k79-bus.img').read_bytes()).hexdigest()
assert boot_hash == firmware['boot_after_sha256']
s = (ref.parent/'kernel77/flash-gauge.ps1').read_text().replace('kernel77','kernel79').replace('k77','k79').replace('gauge','bus')
s = s.replace('only_i2c15_status_frequency_and_bus_added','only_gpi0_qup0_i2c1_enabled_and_400khz')
s = s.replace('43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b','3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e')
# Replace only the candidate condition, leaving the rollback digest intact.
s = s.replace("$hash -ne '3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e'", "$hash -ne '"+boot_hash+"'")
assert 'only_i2c15' not in s and "'flash','logdump'" not in s
(ref/'flash-bus.ps1').write_text(s)
s = (ref.parent/'kernel78/reboot-f1.ps1').read_text().replace('kernel78','kernel79').replace("$Prefix='snapshot'","$Prefix='bus'")
(ref/'reboot-f1.ps1').write_text(s)
print('Prepared boot-only deployment:',boot_hash)
