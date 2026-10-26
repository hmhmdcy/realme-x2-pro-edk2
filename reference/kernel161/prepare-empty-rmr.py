from pathlib import Path
import difflib, hashlib, json, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel161')
out = Path('/mnt/e/edk2-samurai-out/kernel161')
out.mkdir(mode=0o700, exist_ok=True)
name = 'drivers/iommu/arm/arm-smmu/arm-smmu.c'
path = kernel / name
before = path.read_text()
assert path.read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=kernel)
compiled = {}
for stage in [156, 157, 158]:
    compiled.update(json.loads((ref.parent / f'kernel{stage}/build-package-validation.json').read_text())['source_sha256'])
for item, digest in compiled.items():
    assert hashlib.sha256((kernel / item).read_bytes()).hexdigest() == digest, item
assert not (out / 'source-before-private.c').exists()
(out / 'source-before-private.c').write_text(before)
(out / 'config-before-private').write_bytes((kernel / '.config').read_bytes())
(out / 'other-diff-before-private.patch').write_bytes(subprocess.check_output(
    ['git', 'diff', '--binary', '--', '.', ':(exclude)' + name], cwd=kernel))
needle = '\tiort_get_rmr_sids(dev_fwnode(smmu->dev), &rmr_list);\n'
assert before.count(needle) == 1
after = before.replace(needle, needle + '''
	/* Do not disturb firmware clients when there are no RMRs to install. */
	if (list_empty(&rmr_list))
		return;
''', 1)
path.write_text(after)
patch = '''Subject: [PATCH] iommu/arm-smmu: avoid disabling clients for an empty RMR list

RMR setup disables client access before installing bypass stream mappings.
Device-tree systems do not provide ACPI IORT RMR entries, but currently
take the same client-disable path even when no entries are available.
Avoid that unnecessary interruption to bootloader scanout. Keep the
existing nonempty RMR setup and normal SMMU reset unchanged.

---

'''
patch += 'diff --git a/' + name + ' b/' + name + '\n'
patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'skip-empty-rmr.patch').write_text(patch)
report = dict(stage=161, baseline_kernel=158, modified_files=[name],
              before_sha256={name: hashlib.sha256(before.encode()).hexdigest()},
              after_sha256={name: hashlib.sha256(after.encode()).hexdigest()},
              previous_display_fixes_all_preserved=True, config_unchanged=True,
              normal_smmu_reset_unchanged=True, nonempty_rmr_path_unchanged=True,
              global_dma_bypass_not_enabled=True, deployed=False,
              physical_startup_corruption_root_cause_confirmed=False)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
