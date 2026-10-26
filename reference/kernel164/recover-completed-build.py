from pathlib import Path
import hashlib, json, re, shutil, subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
target = out / 'firmware'
log = (target / 'firmware-build-private.log').read_text()
baseline = Path('/mnt/e/edk2-samurai-out/kernel132/canonical-firmware/firmware-build.log').read_text()
warning = lambda text: [line for line in text.splitlines() if re.search(r'\b(?:warning|error):', line, re.I)]
diagnostics = warning(log)
assert all(line in set(warning(baseline)) and 'warning: Suspicious expression:' in line for line in diagnostics)
assert '- Done -' in log
source = json.loads((ref / 'source-validation.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, digest in source['after_sha256'].items():
    assert sha(repo / name) == digest
blob = repo / 'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
assert blob.read_bytes() == (target / 'source-before.dtb').read_bytes()
assert subprocess.check_output(['git', 'diff', '--binary', '--', '.'] + [':(exclude)' + name for name in source['modified_files']], cwd=repo) == (out / 'other-diff-before-private.patch').read_bytes()
fv = repo / 'workspace/Build/samurai/RELEASE_GCC5/FV'
for name, path in [('boot-panel-handoff.img', repo / 'boot-samurai.img'),
                   ('firmware-after.fd', fv / 'SM8150_UEFI.fd'), ('fvmain-after.Fv', fv / 'FVMAIN.Fv'),
                   ('fvcompact-after.Fv', fv / 'FVMAIN_COMPACT.Fv')]:
    assert not (target / name).exists()
    shutil.copyfile(path, target / name)
report = dict(stage=164, kernel_build_kept=163, full_firmware_build_pass=True,
              new_compiler_warnings=0, legacy_configuration_warning_count=len(diagnostics),
              distinct_legacy_warning_templates=len(set(diagnostics)), legacy_warning_templates_match132=True,
              candidate_embedded_dtb_sha256=sha(target / 'firmware-after.dtb'),
              candidate_dtb_matches_current163=True, original_repository_dtb_restored=True,
              source_sha256=source['after_sha256'], firmware_module_audit_pending=True,
              candidate_boot_bytes=(target / 'boot-panel-handoff.img').stat().st_size,
              candidate_boot_sha256=sha(target / 'boot-panel-handoff.img'), deployed=False)
(ref / 'firmware-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
