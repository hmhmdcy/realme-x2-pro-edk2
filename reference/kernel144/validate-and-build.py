from pathlib import Path
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144')
out = Path('/mnt/e/edk2-samurai-out/kernel144')
meta = json.loads((ref / 'source-preparation-validation.json').read_text())
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
assert tests['actual_functions_tested'] and tests['candidate_cases'] == 26
assert all(item['returncode'] == 0 for item in tests['results'].values())
source = root / 'drivers/tty/serial/eud.c'
assert hashlib.sha256(source.read_bytes()).hexdigest() == meta['candidate_source_sha256']
assert source.read_bytes() == (out / 'eud-candidate-private.c').read_bytes()
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()

def split_diff(data):
    return {block.split(b'\n', 1)[0]: block for block in
            re.split(rb'(?m)(?=^diff --git )', data) if block}

before = split_diff((out / 'source-diff-before-private.patch').read_bytes())
after = split_diff(subprocess.check_output(['git', '-C', str(root), 'diff', '--binary']))
assert before.keys() == after.keys()
assert [key for key in before if before[key] != after[key]] == [
    b'diff --git a/drivers/tty/serial/eud.c b/drivers/tty/serial/eud.c']
dma = json.loads(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel140/dma-diagnostic-source-validation.json').read_text())
assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
           for name, digest in dma['files'].items())
check = subprocess.run(['perl', str(root / 'scripts/checkpatch.pl'), '--no-signoff',
                        '--ignore', 'COMMIT_MESSAGE', str(ref / 'eud-reboot-handoff.patch')],
                       capture_output=True, text=True)
(out / 'checkpatch-private.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0, 'Check private checkpatch diagnostics'
source_report = dict(stage=144, source_sha256=meta['candidate_source_sha256'],
                     only_changed_source_from143='drivers/tty/serial/eud.c',
                     full_git_diff_outside_eud_byte_identical=True,
                     kernel_config_unchanged=True, slimbus139_and_dma140_preserved=True,
                     checkpatch_code_errors=0, checkpatch_code_warnings=0,
                     actual_function_cases=26, deployed=False, goal_complete=False)
(ref / 'source-validation.json').write_text(json.dumps(source_report, indent=2) + '\n')
print('K144_SOURCE_SCOPE_AND_26_ACTUAL_FUNCTION_CASES_VERIFIED', flush=True)

env = os.environ.copy()
env['PATH'] = '/home/cy122/.cargo/bin:' + env['PATH']
env['RUSTUP_HOME'] = '/home/cy122/.rustup'
env['KBUILD_BUILD_VERSION'] = '144'
base = ['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-']
retry = sys.argv[1:] == ['--retry-low-memory']
assert not sys.argv[1:] or retry
if retry:
    assert not (ref / 'build-validation.json').exists()
    assert json.loads((ref / 'build-interruption-validation.json').read_text())['image_link_interrupted']
    relocation = json.loads((out / 'relocated-rejected134-image-private.json').read_text(encoding='utf-8-sig'))
    assert relocation['destination_verified'] and relocation['source_removed']
    assert shutil.disk_usage('/mnt/e').free > 1024**3
    # The prior WSL process is terminal; delete only incomplete generated files.
    removed = []
    for path in list(root.rglob('*.o')) + [root / 'vmlinux.unstripped', root / '.tmp_vmlinux1', root / '.tmp_vmlinux2']:
        if path.is_file() and path.stat().st_size == 0:
            assert path.resolve().is_relative_to(root.resolve())
            removed.append(str(path.relative_to(root)))
            path.unlink()
    (out / 'zero-intermediates-removed-private.json').write_text(json.dumps(removed, indent=2) + '\n')
    base.append('LD=aarch64-linux-gnu-ld --no-keep-memory')

def constrain_build():
    if retry:
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))

def make(name, args):
    log = out / (name + '-build-private.log')
    assert not log.exists(), 'Completed or interrupted build must be inspected before retry'
    with log.open('wb') as stream:
        result = subprocess.run(base + args, cwd=root, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, preexec_fn=constrain_build)
    assert result.returncode == 0, 'Check private build diagnostics: ' + name
    print('K144_' + name.upper() + '_BUILD_EXIT0', flush=True)
    return log

prefix = 'handoff-retry' if retry else 'handoff'
jobs = '-j2' if retry else '-j8'
object_log = make(prefix + '-object', ['W=1', jobs, 'drivers/tty/serial/eud.o'])
assert not re.search(r'\b(?:warning|error):', object_log.read_text()), 'New EUD object diagnostics'
image_log = make(prefix + '-image', [jobs, 'Image', 'modules', 'qcom/sm8150-samurai.dtb'])
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
assert (root / 'include/config/kernel.release').read_text().strip() == '7.3.0-rc6-rmx1931-samurai-k132+'
assert source.read_bytes() == (out / 'eud-candidate-private.c').read_bytes()
files = {}
for relative, name in [
        ('arch/arm64/boot/Image', 'Image-k144-eud-handoff-private'),
        ('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'sm8150-samurai-k144-private.dtb'),
        ('System.map', 'System-k144-private.map')]:
    target = out / name
    assert not target.exists()
    shutil.copyfile(root / relative, target)
    files[name] = dict(bytes=target.stat().st_size,
                       sha256=hashlib.sha256(target.read_bytes()).hexdigest())
assert files['sm8150-samurai-k144-private.dtb']['sha256'] == '97501daa5639223c018a19c120bce1dbcf45f60abcd404c406c4ee67821d6aa8'
report = dict(stage=144, source_sha256=meta['candidate_source_sha256'],
              image_modules_dtb_build_completed=True, eud_w1_warnings=0,
              reduced_memory_linker_retry=retry, build_address_space_cap_gib=3 if retry else None,
              module_objects=len(list(root.rglob('*.ko'))), dtb_matches132=True,
              kernel_config_unchanged=True, files=files,
              complete_flash_package_prepared=False, deployed=False,
              display_accepted=False, gpu_accepted=False, charging_accepted=False,
              real_host_f1_receipt_verified=False, goal_complete=False)
(ref / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
meta['kernel_build_completed'] = True
(ref / 'source-preparation-validation.json').write_text(json.dumps(meta, indent=2) + '\n')
print('K144_IMAGE_MODULES_DTB_BUILD_COMPLETE_NOT_DEPLOYED', flush=True)
