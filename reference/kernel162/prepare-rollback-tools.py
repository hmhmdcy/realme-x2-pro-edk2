from pathlib import Path
import ast, hashlib, json, shutil, tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel162'
out = Path('/mnt/e/edk2-samurai-out/kernel162')
out.mkdir(mode=0o700, exist_ok=True)
pre = ['collect-preflash.py', 'quiesce-current158.sh', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'enter-bootloader.ps1']
post = ['capture-startup.py', 'k160-startup-trace', 'display-power.py', 'capture-display-cycles.py', 'verify-runtime.py', 'capture-boot-timing.py', 'poll-first-boot.ps1']
files = []
for name in pre + post:
    text = (root / 'reference/kernel160' / name).read_text()
    for before, after in [('kernel160', 'kernel162'), ('k160', 'k162'), ('K160', 'K162'), ('stage=160', 'stage=162'), ('same158-third', 'rollback158')]:
        text = text.replace(before, after)
    if name in pre:
        text = text.replace('#158 ', '#161 ').replace('CURRENT158', 'CURRENT161')
        if name.endswith('.py'):
            text = text.replace("read_text().strip()=='0'", "read_text().strip()=='512'")
        if name.endswith('.sh'):
            text = text.replace('tainted)" = 0', 'tainted)" = 512')
    if name == 'collect-preflash.py':
        text = text.replace("assert prior.count('WARNING:')==0", "assert prior.count('WARNING:')==1\nassert 'WARNING: sound/soc/codecs/wcd934x.c:1457' in prior\nassert 'Efuse sense is not complete val=0, ret=-22' in prior")
    if name == 'check-quiesce.py':
        text = text.replace("assert current.count('WARNING:')==prior.count('WARNING:')==0", "assert current.count('WARNING:')==prior.count('WARNING:')==1\nassert 'WARNING: sound/soc/codecs/wcd934x.c:1457' in current\nassert 'Efuse sense is not complete val=0, ret=-22' in current")
        text = text.replace('taint=0,current_kernel=158', 'taint=512,current_kernel=161')
        text = text.replace('known_baseline_gpu_faults=0', 'known_audio_warning_for_shutdown_only=True,known_baseline_gpu_faults=0')
    destination = ref / name.replace('k160', 'k162').replace('quiesce-current158', 'quiesce-current161')
    assert not destination.exists(), destination
    if destination.suffix == '.py':
        ast.parse(text)
    destination.write_text(text)
    if destination.suffix != '.ps1':
        files.append(destination)
build = root / 'reference/kernel158/build-package-validation.json'
archive = out / 'rollback-tools-private.tar'
assert not archive.exists()
with tarfile.open(archive, 'w') as stream:
    for path in files:
        stream.add(path, arcname=path.name)
    stream.add(build, arcname='build-package-validation.json')
shutil.copyfile(build, out / 'build-package-validation.json')
image = out / 'logdump-k158-rollback.img'
assert not image.exists()
shutil.copyfile(out.parent / 'kernel158/logdump-k158-before-ctl.img', image)
expected = json.loads(build.read_text())['logdump_sha256']
assert hashlib.sha256(image.read_bytes()).hexdigest() == expected
report = dict(stage=162, actual_target_kernel=158, source_kernel=161,
              rollback_image_sha256=expected, new_build=False,
              known_audio_warning_accepted_only_to_quiesce_failed_boot=True,
              target_runtime_still_requires_zero_warnings_and_taint=True,
              tools_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(ref / 'rollback-tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
