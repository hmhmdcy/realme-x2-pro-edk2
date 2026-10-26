from pathlib import Path
import ast, hashlib, json, tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel164'
out = Path('/mnt/e/edk2-samurai-out/kernel164')
files = []
pre = ['collect-preflash.py', 'quiesce-current158.sh', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'enter-bootloader.ps1']
post = ['capture-startup.py', 'k160-startup-trace', 'display-power.py', 'capture-boot-timing.py', 'verify-runtime.py', 'poll-first-boot.ps1']
for name in pre + post:
    text = (root / 'reference/kernel160' / name).read_text()
    for before, after in [('kernel160', 'kernel164'), ('k160', 'k164'), ('K160', 'K164'),
                          ('stage=160', 'stage=164'), ('#158 ', '#163 '), ('kernel_build=158', 'kernel_build=163'),
                          ('CURRENT158', 'CURRENT163'), ('current_kernel=158', 'current_kernel=163'),
                          ('target_kernel=158', 'target_kernel=163'), ('same158-third', 'firmware164')]:
        text = text.replace(before, after)
    if name == 'verify-runtime.py':
        text = text.replace("assert hashes['/dev/sde11']==original['/dev/sde11']", "firmware=json.loads(Path('/var/lib/samurai/k164-tools/boot-package-validation.json').read_text())\nassert hashes['/dev/sde11']==firmware['boot_sha256']")
        text = text.replace('boot_and_persist_preserved=True', 'boot164_readback_exact=True,persist_preserved=True,logdump163_preserved=True')
        text = text.replace('preservation_reference_from_current158_before_same_image_reboot=True', 'preservation_reference_from_current163_before_firmware_update=True')
    if name == 'poll-first-boot.ps1':
        text = text.replace('New158', 'New163')
    destination = ref / name.replace('k160', 'k164').replace('quiesce-current158', 'quiesce-current163')
    assert not destination.exists()
    if destination.suffix == '.py':
        ast.parse(text)
    destination.write_text(text)
    if destination.suffix != '.ps1':
        files.append(destination)
capture = (root / 'reference/kernel163/capture-display-cycles.py').read_text().replace('k163', 'k164')
(ref / 'capture-display-cycles.py').write_text(capture)
files.append(ref / 'capture-display-cycles.py')
steady = (root / 'reference/kernel163/observe-steady.py').read_text().replace('k163', 'k164').replace('stage=163', 'stage=164')
(ref / 'observe-steady.py').write_text(steady)
files.append(ref / 'observe-steady.py')
archive = out / 'deployment-tools-private.tar'
assert not archive.exists()
with tarfile.open(archive, 'w') as stream:
    for path in files:
        stream.add(path, arcname=path.name)
    stream.add(root / 'reference/kernel163/build-package-validation.json', arcname='build-package-validation.json')
    stream.add(ref / 'boot-package-validation.json', arcname='boot-package-validation.json')
report = dict(stage=164, current_kernel_required=163, kernel_build_kept=163,
              firmware164_boot_only=True, tools_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(ref / 'deployment-tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
