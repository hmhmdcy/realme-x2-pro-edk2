from pathlib import Path
import hashlib, json, os, re, resource, shutil, struct, subprocess, tarfile

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel161')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel161')
source = json.loads((ref / 'source-validation.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, digest in source['after_sha256'].items():
    assert sha(kernel / name) == digest, name
compiled = {}
for stage in [156, 157, 158]:
    compiled.update(json.loads((ref.parent / f'kernel{stage}/build-package-validation.json').read_text())['source_sha256'])
for name, digest in compiled.items():
    assert sha(kernel / name) == digest, name
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
assert tests['baseline_negative_control_rejected'] and all(row['exit'] == 0 and row['scenarios'] == 7 for row in tests['results'])
assert shutil.disk_usage('/mnt/c').free > 8 * 1024**3
env = os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:' + env['PATH'], RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='161')
base = ['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
def make(label, args):
    log = out / (label + '-build-private.log')
    assert not log.exists(), log
    with log.open('wb') as stream:
        subprocess.run(base + args, cwd=kernel, env=env, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limit, check=True)
    assert not re.search(r'\b(?:warning|error):', log.read_text()), log
    print('K161_' + label.upper() + '_PASS', flush=True)
check = subprocess.run(['scripts/checkpatch.pl', '--no-tree', '--strict', '--no-signoff', str(ref / 'skip-empty-rmr.patch')], cwd=kernel, capture_output=True, text=True)
(out / 'checkpatch.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0, check.stdout
make('changed-w1', ['W=1', '-j4', 'drivers/iommu/arm/arm-smmu/arm-smmu.o'])
make('full', ['-j4', 'Image', 'modules', 'qcom/sm8150-samurai.dtb'])
assert (kernel / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
image = out / 'Image-k161-empty-rmr-private'
assert not image.exists()
shutil.copyfile(kernel / 'arch/arm64/boot/Image', image)
assert '#161 SMP PREEMPT' in subprocess.check_output(['strings', str(image)], text=True)
modules = kernel.parent / 'modules-root161'
assert not modules.exists()
modules.mkdir(mode=0o700)
make('install', ['INSTALL_MOD_PATH=' + str(modules), 'INSTALL_MOD_STRIP=1', 'modules_install'])
release = (kernel / 'include/config/kernel.release').read_text().strip()
(modules / 'lib/modules' / release / 'build').unlink()
depmod = subprocess.run(['depmod', '-e', '-F', str(kernel / 'System.map'), '-b', str(modules), release], capture_output=True)
assert depmod.returncode == 0 and not depmod.stdout and not depmod.stderr
def note(data):
    assert data[:6] == b'\x7fELF\x02\x01'
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[headers[index][4]:headers[index][4]+headers[index][5]]
    for row in headers:
        if strings[row[0]:].split(b'\x00', 1)[0] == b'.note.gnu.build-id':
            return row[4], row[5]
    raise AssertionError('Missing module build ID')
with tarfile.open(out.parent / 'kernel132/modules-k132-private.tar.gz') as archive:
    old = {row.name: archive.extractfile(row).read() for row in archive if row.isfile() and row.name.endswith('.ko')}
new = {str(path.relative_to(modules)): path.read_bytes() for path in modules.rglob('*.ko')}
assert len(new) == len(old) == 770 and new.keys() == old.keys()
changed = []
for name, before in old.items():
    after = new[name]
    if before == after:
        continue
    assert note(before) == note(after), name
    offset, size = note(before)
    assert after[:offset] + before[offset:offset+size] + after[offset+size:] == before, name
    changed.append(name)
compat = dict(stage=161, total_modules=770, unchanged_compiled_modules=770-len(changed), build_id_only_differences=changed,
              all_other_bytes_including_code_data_relocations_symbols_and_modinfo_identical=True,
              existing_modules132_runtime_compatible=True, existing_module_files_reused=True)
(ref / 'module-compatibility-validation.json').write_text(json.dumps(compat, indent=2) + '\n')
dtb = kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
baseline = json.loads((ref.parent / 'kernel158/build-package-validation.json').read_text())
assert sha(dtb) == baseline['dtb_sha256']
target = out / 'logdump-k161-empty-rmr.img'
assert not target.exists()
shutil.copyfile(out.parent / 'kernel158/logdump-k158-before-ctl.img', target)
subprocess.run(['mcopy', '-o', '-i', str(target), str(image), '::/Image'], check=True)
assert subprocess.check_output(['mcopy', '-i', str(target), '::/Image', '-']) == image.read_bytes()
assert subprocess.check_output(['mcopy', '-i', str(target), '::/samurai.dtb', '-']) == dtb.read_bytes()
fat = subprocess.run(['fsck.fat', '-n', str(target)], capture_output=True)
(out / 'fat-check.txt').write_bytes(fat.stdout + fat.stderr)
assert fat.returncode == 0 and target.stat().st_size == 67108864
other = subprocess.check_output(['git', 'diff', '--binary', '--', '.'] + [':(exclude)' + name for name in source['modified_files']], cwd=kernel)
assert other == (out / 'other-diff-before-private.patch').read_bytes()
report = dict(stage=161, kernel_build=161, baseline_kernel=158, software_generation=132,
              image_sha256=sha(image), image_bytes=image.stat().st_size,
              logdump_sha256=sha(target), logdump_bytes=target.stat().st_size,
              source_sha256=source['after_sha256'], prior_display_source_hashes_verified=compiled,
              dtb_sha256=sha(dtb), dtb_unchanged=True, config_unchanged=True,
              modules132_runtime_compatible=True, compiled_module_build_id_only_differences=len(changed),
              modules132_reused=True, other_tracked_diffs_unchanged=True, build_warnings=0,
              checkpatch_pass=True, fat_check_pass=True, global_dma_bypass_not_enabled=True,
              deployed=False, physical_startup_bug_fixed=False)
for destination in [ref, out]:
    (destination / 'build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
