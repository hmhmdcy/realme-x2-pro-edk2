from pathlib import Path
import ast
import shutil
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
prev = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
def save(name, text):
    assert not (ref / name).exists(), name
    if name.endswith('.py'):
        ast.parse(text)
    (ref / name).write_text(text)
for name in ['dtb-before', 'boot-before.img']:
    assert not (out / name).exists()
    shutil.copy2(out.parent / 'kernel134' / name, out / name)
for name in ['build-canonical-firmware.sh', 'verify-original-restore.py', 'audit-firmware.py']:
    t = (prev / name).read_text().replace('kernel134', 'kernel135').replace('k134', 'k135').replace('-usb-input.img', '-mdss-reset.img')
    if name == 'audit-firmware.py':
        t = t.replace("prior=base_out.parent/'kernel132/canonical-firmware'", "prior=base_out.parent/'kernel134/canonical-firmware'")
        t = t.replace("prior/'boot-k132-charger.img'", "prior/'boot-k134-usb-input.img'")
        t = t.replace('actual_device_boot_132_executables_preserved', 'actual_device_boot_134_executables_preserved')
    save(name, t)
t = (prev / 'collect-preflash.sh').read_text()
t = t.replace('k134-preflash', 'k135-preflash').replace('k134-keytrace', 'k135-keytrace').replace('/tmp/k134-', '/tmp/k135-')
t = t.replace('k132-first-runtime', 'k134-recovered-runtime').replace('-k132+', '-k134+')
t = t.replace('/var/lib/samurai/k132-preflash/new-module-tree.sha256', '/var/lib/samurai/k134-preflash/new-module-tree.sha256')
t = t.replace('old132', 'old134').replace('/dev/dri/card1', '/dev/dri/card0').replace('card1-DSI-1', 'card0-DSI-1')
t = t.replace('K134_FRESH132', 'K135_FRESH134')
t = t.replace('cat /sys/firmware/fdt >', 'sha256sum /etc/greetd/samurai-phosh.toml /usr/local/bin/samurai-phosh-session /etc/conf.d/greetd > "$dest/gui-config.sha256"\ncat /sys/firmware/fdt >')
save('collect-preflash.sh', t)
t = (prev / 'verify-preflash.py').read_text().replace("ref=r/'reference/kernel134'", "ref=r/'reference/kernel135'").replace("out=Path('/mnt/e/edk2-samurai-out/kernel134')", "out=Path('/mnt/e/edk2-samurai-out/kernel135')")
t = t.replace('-k132+', '-k134+').replace("b'#132 SMP'", "b'#134 SMP'").replace('kernel132/embedded-boot-id-private.txt', 'kernel134/embedded-boot-id-private.txt').replace('old132', 'old134')
t = t.replace('501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6', 'a8c6a26b14c7e2b6ac95f78f41aff937b62c705c974fc96c1367c2626e6fd73d').replace('db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751', '9c9175c5cfa6b840c4395576ec552e5f64a92e12c3a04fe1068db249e2070282')
t = t.replace('boot-partition-k132-charger.img', 'boot-partition-k134-usb-input.img').replace('logdump-k132-charger.img', 'logdump-k134-usb-input.img').replace("out.parent/'kernel132'/filename", "out.parent/'kernel134'/filename")
t = t.replace('current_kernel=132,target_kernel=134', 'current_kernel=134,target_kernel=134,dt_variant=135').replace('K134_CURRENT132', 'K135_CURRENT134')
save('verify-preflash.py', t)
t = (prev / 'quiesce-current132.sh').read_text().replace('k134-preflash', 'k135-preflash').replace('k134-quiesce', 'k135-quiesce').replace("'^#132 '", "'^#134 '").replace('-k132+', '-k134+')
t = t.replace('/dev/dri/card1', '/dev/dri/card0').replace('/dri/1/', '/dri/0/').replace('$before/new-module-tree.sha256', '$before/old134-module-tree.sha256').replace('K134_CURRENT132', 'K135_CURRENT134')
save('quiesce-current134.sh', t)
t = (prev / 'verify-quiesce.py').read_text().replace('kernel134', 'kernel135').replace('current_kernel=132,target_kernel=134', 'current_kernel=134,target_kernel=134,dt_variant=135').replace('drm_minor=1', 'drm_minor=0').replace('staged134_module_checks_pass', 'reused134_module_checks_pass').replace('K134_CURRENT132', 'K135_CURRENT134')
save('verify-quiesce.py', t)
t = (prev / 'freeze-for-bootloader.sh').read_text().replace('k134-preflash', 'k135-preflash').replace('k134-quiesce', 'k135-quiesce').replace("'^#132 '", "'^#134 '").replace('/dev/dri/card1', '/dev/dri/card0').replace('/dri/1/', '/dri/0/').replace('$before/new-module-tree.sha256', '$before/old134-module-tree.sha256').replace('/run/k134-', '/run/k135-').replace('K134_', 'K135_')
save('freeze-for-bootloader.sh', t)
for name in ['enter-bootloader.ps1', 'enable-eud.ps1', 'observe-current-fastboot.ps1', 'poll-new-boot.ps1']:
    t = (prev / name).read_text().replace('kernel134', 'kernel135').replace('k134-', 'k135-').replace('K134_', 'K135_').replace('usb-input-first', 'mdss-reset-first')
    # The software banner remains 134; this is an explicitly recorded DT-only variant.
    save(name, t)
print('K135_DT_ONLY_VARIANT_TOOLS_WITH_CURRENT134_IDENTITY_AND_CARD0_GUARDS_READY', flush=True)
