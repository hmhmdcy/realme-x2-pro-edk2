from pathlib import Path
import ast
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
prev = r / 'reference/kernel132'
assert not (ref / 'package-boot.py').exists()
t = (prev / 'package-boot.py').read_text().replace('kernel132', 'kernel134').replace('k132', 'k134').replace('candidate=132', 'candidate=134').replace('actual_device_boot_129', 'actual_device_boot_132')
t = t.replace('-charger.img', '-usb-input.img')
ast.parse(t)
(ref / 'package-boot.py').write_text(t)
t = (prev / 'verify-live-staging.py').read_text().replace('kernel132', 'kernel134').replace('k132', 'k134').replace('K132', 'K134')
t = t.replace('old129', 'old132').replace('new132_directory', 'new134_directory').replace('old118_and126_and129', 'old118_and126_and132').replace('current_kernel_still129', 'current_kernel_still132')
ast.parse(t)
(ref / 'verify-live-staging.py').write_text(t)
t = (prev / 'quiesce-current129.sh').read_text().replace('k132', 'k134').replace('K132', 'K134').replace('k129', 'k132').replace('CURRENT129', 'CURRENT132').replace("'^#129 '", "'^#132 '")
(ref / 'quiesce-current132.sh').write_text(t)
t = (prev / 'verify-quiesce.py').read_text().replace('kernel132', 'kernel134').replace('K132', 'K134')
t = t.replace('current_kernel=129,target_kernel=132', 'current_kernel=132,target_kernel=134').replace('staged132', 'staged134').replace('CURRENT129', 'CURRENT132')
ast.parse(t)
(ref / 'verify-quiesce.py').write_text(t)
t = (prev / 'freeze-for-bootloader.sh').read_text().replace('k132', 'k134').replace('K132', 'K134').replace("'^#129 '", "'^#132 '")
(ref / 'freeze-for-bootloader.sh').write_text(t)
for name in ['enter-bootloader.ps1', 'observe-current-fastboot.ps1', 'enable-eud.ps1', 'poll-new-boot.ps1', 'collect-runtime.sh', 'inspect-runtime.py', 'flash-validated132.ps1']:
    t = (prev / name).read_text().replace('kernel132', 'kernel134').replace('k132', 'k134').replace('K132', 'K134').replace('charger-node-first', 'usb-input-first').replace('-charger.img', '-usb-input.img')
    if name == 'flash-validated132.ps1':
        t = t.replace('candidate-package-validation.json', 'kernel-build-validation.json')
        t = t.replace('$build.candidate -ne 132', '$build.candidate -ne 134').replace('all_770_module_executable_sections_byte_equal129', 'all_existing_module_executable_sections_equal132').replace('charger_driver_unchanged', 'mp2650_driver_unchanged')
        t = t.replace('$before.current_kernel -ne 129', '$before.current_kernel -ne 132').replace('$before.target_kernel -ne 132', '$before.target_kernel -ne 134')
        t = t.replace('new132_directory', 'new134_directory').replace('old118_and126_and129', 'old118_and126_and132').replace('Fresh129', 'Fresh132').replace('Current129', 'Current132').replace('kernel_build=132', 'kernel_build=134')
    if name in ['collect-runtime.sh', 'inspect-runtime.py', 'poll-new-boot.ps1']:
        t = t.replace("'^#132 '", "'^#134 '").replace('#132 SMP PREEMPT', '#134 SMP PREEMPT').replace('kernel_build=132', 'kernel_build=134')
        t = t.replace('embedded132', 'embedded134')
    if name == 'collect-runtime.sh':
        t = t.replace('dmesg > "$dest/dmesg.txt"', '''test -d /sys/class/power_supply/samurai-usb-input
cat /sys/class/power_supply/samurai-usb-input/uevent > "$dest/usb-input-uevent.txt"
stat -c '%a %n' /sys/class/power_supply/samurai-usb-input/online /sys/class/power_supply/samurai-usb-input/usb_type /sys/class/power_supply/samurai-usb-input/current_max > "$dest/usb-input-modes.txt"
readlink -f /sys/class/power_supply/samurai-usb-input/device/of_node > "$dest/usb-input-of-node.txt"
dmesg > "$dest/dmesg.txt"''').replace('KERNEL129_FIRST', 'KERNEL134_FIRST')
    if name == 'inspect-runtime.py':
        anchor = 'report=dict('
        t = t.replace(anchor, '''node='/soc@0/spmi@c440000/pmic@2/usb-input@1300'
assert live[node]['compatible']==b'realme,rmx1931-usb-input\\0' and live[node]['reg']==(0x1300).to_bytes(4,'big')
assert b'POWER_SUPPLY_ONLINE=1\\n' in data['usb-input-uevent.txt']
assert b'POWER_SUPPLY_USB_TYPE=' in data['usb-input-uevent.txt'] and b'POWER_SUPPLY_CURRENT_MAX=' in data['usb-input-uevent.txt']
assert len(data['usb-input-modes.txt'].splitlines())==3 and all(l.startswith(b'444 ') for l in data['usb-input-modes.txt'].splitlines())
assert data['usb-input-of-node.txt'].strip().endswith(node.encode())
assert data['state.txt'].splitlines()[-1]==b'0' and data['phosh.txt'].strip() and data['phoc.txt'].strip()
report=dict(usb_input_standard_power_supply_auto_registered=True,usb_input_attributes_read_only=True,''')
    if name.endswith('.py'):
        ast.parse(t)
    target = 'flash-validated134.ps1' if name == 'flash-validated132.ps1' else name
    (ref / target).write_text(t)
print('K134_CANONICAL_PACKAGE_PARALLEL_STAGING_AND_CURRENT132_SINGLE_FLASH_TOOLS_READY', flush=True)
