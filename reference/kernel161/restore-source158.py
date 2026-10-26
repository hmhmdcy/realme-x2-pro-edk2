from pathlib import Path
import hashlib, json, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel161')
out = Path('/mnt/e/edk2-samurai-out/kernel161')
name = 'drivers/iommu/arm/arm-smmu/arm-smmu.c'
source = json.loads((ref / 'source-validation.json').read_text())
path = kernel / name
assert hashlib.sha256(path.read_bytes()).hexdigest() == source['after_sha256'][name]
snapshot = out / 'source-rejected161-private.c'
assert not snapshot.exists()
snapshot.write_bytes(path.read_bytes())
path.write_bytes((out / 'source-before-private.c').read_bytes())
assert hashlib.sha256(path.read_bytes()).hexdigest() == source['before_sha256'][name]
assert path.read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=kernel)
build = json.loads((ref / 'build-package-validation.json').read_text())
for other, digest in build['prior_display_source_hashes_verified'].items():
    assert hashlib.sha256((kernel / other).read_bytes()).hexdigest() == digest, other
assert (kernel / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
assert subprocess.check_output(['git', 'diff', '--binary', '--', '.', ':(exclude)' + name], cwd=kernel) == (out / 'other-diff-before-private.patch').read_bytes()
report = dict(stage=161, candidate_rejected_for_new_boot_warning_and_dma_failures=True,
              source_restored_to158=True, prior_display_source_hashes_preserved=True,
              other_tracked_diffs_preserved=True, config_unchanged=True,
              generated_main_image_still161_and_not_a_rollback_image=True,
              rollback_uses_immutable_verified_original158_image=True,
              causal_link_between_rmr_candidate_and_audio_failures_unproven=True)
(ref / 'source-restoration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
