from pathlib import Path
import ast
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
assert not (ref / 'record-complete-bundle.py').exists()
t = (r / 'reference/kernel132/record-complete-bundle.py').read_text()
t = t.replace('kernel132', 'kernel134').replace('k132', 'k134').replace('K132', 'K134').replace('image-export132', 'image-export134').replace('rootfs132', 'rootfs134')
t = t.replace('candidate_kernel=132', 'candidate_kernel=134').replace('rootfs_generation=132', 'rootfs_generation=134').replace("== 132", "== 134").replace('-charger.img', '-usb-input.img')
t = t.replace('ENCODED132', 'ENCODED134').replace('encoded132', 'encoded134')
t = t.replace("assert runtime['new_boot_verified']", "assert runtime['usb_input_standard_power_supply_auto_registered'] and power['usb_input_standard_nonempty_uevents'] == 8\nassert runtime['new_boot_verified']")
t = t.replace('persistent_mp2650_auto_registration_actual_new_boot_verified=True,', 'persistent_mp2650_auto_registration_actual_new_boot_verified=True,\n              usb_input_auto_registration_actual_new_boot_verified=True,')
ast.parse(t)
(ref / 'record-complete-bundle.py').write_text(t)
print('K134_MATCHING_FOUR_ARTIFACTS_AND_REAL_BOOT_BUNDLE_AUDIT_TOOLS_READY', flush=True)
