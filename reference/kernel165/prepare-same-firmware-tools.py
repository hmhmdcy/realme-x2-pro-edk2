from pathlib import Path
import ast, hashlib, json, tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel165'
out = Path('/mnt/e/edk2-samurai-out/kernel165')
out.mkdir(mode=0o700, exist_ok=True)
pre = ['collect-preflash.py', 'quiesce-current163.sh', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'enter-bootloader.ps1']
post = ['capture-startup.py', 'k164-startup-trace', 'display-power.py', 'capture-boot-timing.py', 'verify-runtime.py', 'poll-first-boot.ps1', 'capture-display-cycles.py', 'observe-steady.py', 'read-firmware-log-mmap.py']
files = []
for name in pre + post:
    text = (root / 'reference/kernel164' / name).read_text()
    for before, after in [('kernel164', 'kernel165'), ('k164', 'k165'), ('K164', 'K165'),
                          ('stage=164', 'stage=165'), ('firmware164', 'same164-second')]:
        text = text.replace(before, after)
    if name in pre:
        text = text.replace("read_text().strip()=='0'", "read_text().strip()=='512'")
        text = text.replace('tainted)" = 0', 'tainted)" = 512')
    if name == 'collect-preflash.py':
        text = text.replace("assert prior.count('WARNING:')==0", "assert prior.count('WARNING:')==1\nassert 'WARNING: sound/soc/codecs/wcd934x.c:1457' in prior\nassert 'Efuse sense is not complete val=0, ret=-22' in prior")
    if name == 'check-quiesce.py':
        text = text.replace("assert current.count('WARNING:')==prior.count('WARNING:')==0", "assert current.count('WARNING:')==prior.count('WARNING:')==1\nassert 'WARNING: sound/soc/codecs/wcd934x.c:1457' in current\nassert 'Efuse sense is not complete val=0, ret=-22' in current")
        text = text.replace('taint=0,current_kernel=163', 'taint=512,current_kernel=163')
        text = text.replace('known_baseline_gpu_faults=0', 'known_audio_warning_for_shutdown_only=True,known_baseline_gpu_faults=0')
    if name == 'verify-runtime.py':
        text = text.replace('boot164_readback_exact=True', 'boot164_readback_exact=True,same_firmware_second_boot=True')
    destination = ref / name.replace('k164', 'k165')
    assert not destination.exists()
    if destination.suffix == '.py':
        ast.parse(text)
    destination.write_text(text)
    if destination.suffix != '.ps1':
        files.append(destination)
archive = out / 'same-firmware-tools-private.tar'
assert not archive.exists()
with tarfile.open(archive, 'w') as stream:
    for path in files:
        stream.add(path, arcname=path.name)
    stream.add(root / 'reference/kernel163/build-package-validation.json', arcname='build-package-validation.json')
    stream.add(root / 'reference/kernel164/boot-package-validation.json', arcname='boot-package-validation.json')
report = dict(stage=165, kernel_build_kept=163, firmware_kept=164, new_flash=False,
              known_audio_warning_accepted_only_for_shutdown=True,
              tools_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(ref / 'tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
