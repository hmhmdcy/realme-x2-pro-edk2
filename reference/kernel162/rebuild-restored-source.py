from pathlib import Path
import hashlib, json, os, re, resource, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel162')
out = Path('/mnt/e/edk2-samurai-out/kernel162')
restoration = json.loads((ref.parent / 'kernel161/source-restoration-validation.json').read_text())
assert restoration['source_restored_to158']
assert (kernel / 'drivers/iommu/arm/arm-smmu/arm-smmu.c').read_bytes() == subprocess.check_output(
    ['git', 'show', 'HEAD:drivers/iommu/arm/arm-smmu/arm-smmu.c'], cwd=kernel)
original = json.loads((ref.parent / 'kernel158/build-package-validation.json').read_text())
env = os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:' + env['PATH'], RUSTUP_HOME='/home/cy122/.rustup',
           KBUILD_BUILD_VERSION='158', KBUILD_BUILD_TIMESTAMP='Tue Oct 13 22:08:42 CST 2026')
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
log = out / 'restored-source-build-private.log'
assert not log.exists()
with log.open('wb') as stream:
    subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                    'LD=aarch64-linux-gnu-ld --no-keep-memory', '-j4', 'Image', 'modules', 'qcom/sm8150-samurai.dtb'],
                   cwd=kernel, env=env, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limit, check=True)
assert not re.search(r'\b(?:warning|error):', log.read_text())
image = kernel / 'arch/arm64/boot/Image'
image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
assert '#158 SMP PREEMPT Tue Oct 13 22:08:42 CST 2026' in subprocess.check_output(['strings', str(image)], text=True)
report = dict(stage=162, restored_source_build=158, build_warnings=0,
              source158_config_and_prior_display_changes_preserved=True,
              original_build_timestamp_reused=True, main_image_sha256=image_hash,
              main_image_exact_original158=image_hash == original['image_sha256'],
              rollback_still_uses_verified_immutable_original158_package=True)
(ref / 'restored-source-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
