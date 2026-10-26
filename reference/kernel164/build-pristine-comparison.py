from pathlib import Path
import hashlib, json, os, shutil, subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
target = out / 'firmware'
source = json.loads((ref / 'source-validation.json').read_text())
before = json.loads((out / 'source-before-private.json').read_text())
after = {name: (repo / name).read_bytes() for name in source['modified_files']}
for name, data in after.items():
    assert hashlib.sha256(data).hexdigest() == source['after_sha256'][name]
fv = repo / 'workspace/Build/samurai/RELEASE_GCC5/FV'
for name, path in [('boot-panel-handoff.img', repo / 'boot-samurai.img'),
                   ('firmware-after.fd', fv / 'SM8150_UEFI.fd'), ('fvmain-after.Fv', fv / 'FVMAIN.Fv'),
                   ('fvcompact-after.Fv', fv / 'FVMAIN_COMPACT.Fv')]:
    assert not (target / name).exists()
    shutil.copyfile(path, target / name)
blob = repo / 'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
original_blob = blob.read_bytes()
assert original_blob == (target / 'source-before.dtb').read_bytes()
env = os.environ.copy()
env.update(PATH='/home/cy122/.local/bin:' + env['PATH'], CPATH='/home/cy122/edk2-samurai/local/uuid/usr/include',
           LIBRARY_PATH='/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu')
try:
    for name, data in before.items():
        (repo / name).write_text(data)
    shutil.copyfile(target / 'firmware-after.dtb', blob)
    log = target / 'pristine-comparison-build-private.log'
    assert not log.exists()
    with log.open('wb') as stream:
        subprocess.run(['./build.sh', '-d', 'samurai', '--toolchain', 'GCC5', '--skip-rootfs-gen'],
                       cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    for name, path in [('boot-pristine-current.img', repo / 'boot-samurai.img'),
                       ('firmware-pristine-current.fd', fv / 'SM8150_UEFI.fd'), ('fvmain-pristine-current.Fv', fv / 'FVMAIN.Fv'),
                       ('fvcompact-pristine-current.Fv', fv / 'FVMAIN_COMPACT.Fv')]:
        shutil.copyfile(path, target / name)
finally:
    for name, data in after.items():
        (repo / name).write_bytes(data)
    blob.write_bytes(original_blob)
    os.utime(blob, None)
assert subprocess.check_output(['git', 'diff', '--binary', '--', '.'] + [':(exclude)' + name for name in source['modified_files']], cwd=repo) == (out / 'other-diff-before-private.patch').read_bytes()
print('K164_PRISTINE_CURRENT_DTB_COMPARISON_BUILT_SOURCE164_RESTORED', flush=True)
