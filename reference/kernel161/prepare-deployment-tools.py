from pathlib import Path
import ast, hashlib, json, tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel161'
out = Path('/mnt/e/edk2-samurai-out/kernel161')
pre = ['collect-preflash.py', 'quiesce-current158.sh', 'check-quiesce.py',
       'freeze-for-bootloader.sh', 'enter-bootloader.ps1']
post = ['capture-startup.py', 'k160-startup-trace', 'display-power.py',
        'capture-display-cycles.py', 'verify-runtime.py', 'capture-boot-timing.py', 'poll-first-boot.ps1']
files = []
for name in pre + post:
    text = (root / 'reference/kernel160' / name).read_text()
    for before, after in [('kernel160', 'kernel161'), ('k160', 'k161'), ('K160', 'K161'),
                          ('stage=160', 'stage=161'), ('same158-third', 'empty-rmr161')]:
        text = text.replace(before, after)
    if name == 'check-quiesce.py':
        text = text.replace('target_kernel=158', 'target_kernel=161')
    if name in post:
        text = text.replace('#158 ', '#161 ').replace('kernel_build=158', 'kernel_build=161')
        text = text.replace('New158 identity', 'New161 identity').replace('K161_NEW_BOOT_DESKTOP_PRESENT', 'K161_NEW161_BOOT_DESKTOP_PRESENT')
    destination = ref / name.replace('k160', 'k161')
    assert not destination.exists(), destination
    if destination.suffix == '.py':
        ast.parse(text)
    destination.write_text(text)
    if destination.suffix != '.ps1':
        files.append(destination)
archive = out / 'deployment-tools-private.tar'
assert not archive.exists()
with tarfile.open(archive, 'w') as stream:
    for path in files:
        stream.add(path, arcname=path.name)
    stream.add(ref / 'build-package-validation.json', arcname='build-package-validation.json')
report = dict(stage=161, current_kernel_required=158, target_kernel=161,
              tools_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), python_syntax_valid=True)
(ref / 'deployment-tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
