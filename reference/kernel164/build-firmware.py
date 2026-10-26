from pathlib import Path
import hashlib, json, os, re, shutil, subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
target = out / 'firmware'
assert not target.exists()
target.mkdir(mode=0o700)
source = json.loads((ref / 'source-validation.json').read_text())
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
assert all(row['exit'] == 0 and row['scenarios'] == 14 for row in tests['results'])
assert all(row['rejected'] for row in tests['negative_controls'])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, digest in source['after_sha256'].items():
    assert sha(repo / name) == digest, name
blob = repo / 'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
dtb = Path('/home/cy122/pmos-samurai-kernel136/kernel/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')
kernel_build = json.loads((ref.parent / 'kernel163/build-package-validation.json').read_text())
assert sha(dtb) == kernel_build['dtb_sha256']
fv = repo / 'workspace/Build/samurai/RELEASE_GCC5/FV'
for name, path in [('source-before.dtb', blob), ('boot-local-before.img', repo / 'boot-samurai.img'),
                   ('firmware-local-before.fd', fv / 'SM8150_UEFI.fd'), ('fvmain-local-before.Fv', fv / 'FVMAIN.Fv'),
                   ('fvcompact-local-before.Fv', fv / 'FVMAIN_COMPACT.Fv'),
                   ('compat-before.dtb', repo / 'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb')]:
    shutil.copyfile(path, target / name)
env = os.environ.copy()
env.update(PATH='/home/cy122/.local/bin:' + env['PATH'], CPATH='/home/cy122/edk2-samurai/local/uuid/usr/include',
           LIBRARY_PATH='/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu')
try:
    shutil.copyfile(dtb, blob)
    shutil.copyfile(dtb, target / 'firmware-after.dtb')
    log = target / 'firmware-build-private.log'
    with log.open('wb') as stream:
        subprocess.run(['./build.sh', '-d', 'samurai', '--toolchain', 'GCC5', '--skip-rootfs-gen'],
                       cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    diagnostics = [line for line in log.read_text().splitlines() if re.search(r'\b(?:warning|error):', line, re.I)]
    old_log = Path('/mnt/e/edk2-samurai-out/kernel132/canonical-firmware/firmware-build.log').read_text()
    old_diagnostics = set(line for line in old_log.splitlines() if re.search(r'\b(?:warning|error):', line, re.I))
    assert all(line in old_diagnostics and 'warning: Suspicious expression:' in line for line in diagnostics), 'Inspect new compiler diagnostics before packaging'
    for name, path in [('boot-panel-handoff.img', repo / 'boot-samurai.img'),
                       ('firmware-after.fd', fv / 'SM8150_UEFI.fd'), ('fvmain-after.Fv', fv / 'FVMAIN.Fv'),
                       ('fvcompact-after.Fv', fv / 'FVMAIN_COMPACT.Fv')]:
        shutil.copyfile(path, target / name)
finally:
    shutil.copyfile(target / 'source-before.dtb', blob)
    os.utime(blob, None)
for name, digest in source['after_sha256'].items():
    assert sha(repo / name) == digest, name
assert subprocess.check_output(['git', 'diff', '--binary', '--', '.'] + [':(exclude)' + name for name in source['modified_files']], cwd=repo) == (out / 'other-diff-before-private.patch').read_bytes()
report = dict(stage=164, kernel_build_kept=163, full_firmware_build_pass=True, new_compiler_warnings=0,
              legacy_configuration_warning_count=len(diagnostics), legacy_warning_templates_match132=True,
              candidate_embedded_dtb_sha256=sha(target / 'firmware-after.dtb'),
              candidate_dtb_matches_current163=True, original_repository_dtb_restored=True,
              source_sha256=source['after_sha256'], firmware_module_audit_pending=True,
              candidate_boot_bytes=(target / 'boot-panel-handoff.img').stat().st_size,
              candidate_boot_sha256=sha(target / 'boot-panel-handoff.img'), deployed=False)
(ref / 'firmware-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
