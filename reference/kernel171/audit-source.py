from pathlib import Path
import hashlib, json, re, subprocess

ref = Path(__file__).parent
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel171')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
audio = json.loads((ref.parent / 'kernel168/source-validation.json').read_text())
old = json.loads((ref.parent / 'kernel163/build-package-validation.json').read_text())
display = {**old['source_sha256'], **old['prior_display_source_hashes_verified']}
for name, digest in {**audio['source_sha256'], **display}.items():
    assert sha(k / name) == digest, name
assert (k / '.config').read_bytes() == (out.parent / 'kernel168/config-before-private').read_bytes()
dt = json.loads((ref / 'dtb-build-validation.json').read_text())
dts_name = 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert sha(k / dts_name) == dt['dts_after_sha256']
assert sha(k / 'arch/arm64/boot/Image') == dt['image_unchanged_sha256']
assert sha(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == dt['dtb_after_sha256']
assert set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines()) == set(audio['modified_files']) | {dts_name}
check = subprocess.run([str(k / 'scripts/checkpatch.pl'), '--no-tree', '--strict', '--no-signoff', str(ref / 'speaker-sd1.patch')],
                       capture_output=True, text=True)
(out / 'checkpatch-final-private.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0
assert not re.search(r'\b(?:warning|error):', (out / 'dtb-build-private.log').read_text(), re.I)
report = dict(stage=171, kernel_build=168, tracked_modified_files=audio['modified_files'] + [dts_name],
              source_sha256={**audio['source_sha256'], dts_name: dt['dts_after_sha256']},
              image_sha256=dt['image_unchanged_sha256'], dtb_sha256=dt['dtb_after_sha256'],
              display_source_files_unchanged=len(display), config_unchanged=True, checkpatch_pass=True,
              dtb_compile_warnings=0, kernel_not_rebuilt=True)
(ref / 'source-current-validation.json').write_text(json.dumps(report, indent=2) + '\n')
runtime = json.loads((ref / 'runtime-validation.json').read_text())
package = json.loads((ref / 'build-package-validation.json').read_text())
flash = json.loads((out / 'flash-validation.json').read_text(encoding='utf-8-sig'))
assert flash['flash_success'] and runtime['new_boot_vs_preflash'] and runtime['taint'] == 0
assert runtime['partition_hashes']['/dev/sde11'] == package['boot_sha256']
assert runtime['partition_hashes']['/dev/sde32'] == package['logdump_sha256']
deployed = dict(stage=171, kernel_build=168, boot_and_logdump=171, deployed=True, readback_pass=True,
                boot_sha256=package['boot_sha256'], logdump_sha256=package['logdump_sha256'],
                dtb_sd1_gpio140_runtime_verified=True, persist_nv_preserved=True,
                rollback_boot164_and_logdump168_retained=True)
(ref / 'deployment-validation.json').write_text(json.dumps(deployed, indent=2) + '\n')
print(json.dumps(dict(stage=171, source_and_deployment_audit_pass=True, display_sources=len(display), checkpatch=True)))
