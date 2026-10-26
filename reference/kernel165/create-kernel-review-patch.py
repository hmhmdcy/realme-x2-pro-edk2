from pathlib import Path
import hashlib, json, subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = root / 'reference/kernel165'
base = (root / 'reference/kernel158/display-fix-from154.patch').read_text()
addition = (root / 'reference/kernel163/early-panel-reset.patch').read_text()
patch = base[:base.index('diff --git')] + base[base.index('diff --git'):] + '\n' + addition[addition.index('diff --git'):]
destination = ref / 'kernel-display-fix-from154.patch'
destination.write_text(patch)
check = subprocess.run(['git', 'apply', '--reverse', '--check', str(destination)], cwd=kernel, capture_output=True, text=True)
assert check.returncode == 0, check.stdout + check.stderr
source = json.loads((root / 'reference/kernel163/build-package-validation.json').read_text())
expected = dict(source['prior_display_source_hashes_verified'])
expected.update(source['source_sha256'])
for name, digest in expected.items():
    assert hashlib.sha256((kernel / name).read_bytes()).hexdigest() == digest, name
report = dict(stage=165, actual_kernel_build=163, baseline_kernel=154,
              modified_kernel_files=15, reverse_apply_check_pass=True,
              all_15_current_source_hashes_match_compiled_kernel=True,
              firmware164_patch_is_separate_repository=True,
              patch_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
              physical_startup_acceptance_pending=True)
(ref / 'kernel-review-patch-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
