from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
out = ref/'kernel99'
assert not (out/'build-firmware.sh').exists()
source = (ref/'kernel93/build-firmware.sh').read_text()
source = source.replace('kernel93','kernel99').replace('k93-connectivity','k99-haptics').replace('dtb-connectivity','dtb-haptics')
(out/'build-firmware.sh').write_text(source)
source = (ref/'kernel93/verify-firmware.py').read_text()
source = source.replace('kernel93','kernel99').replace('k93-connectivity','k99-haptics')
source = source.replace("assert dt_audit['kernel_audit_pass'] and dt_audit['config_unchanged']", "assert dt_audit['kernel_audit_pass'] and dt_audit['cpio_byte_identical']")
source = source.replace('bluetooth_firmware_selection_only','haptics_bus_and_node_only')
(out/'verify-firmware.py').write_text(source)
print('HAPTICS_FIRMWARE_TOOLS_PREPARED')
