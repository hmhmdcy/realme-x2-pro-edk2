from pathlib import Path
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
previous = json.loads(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144/build-validation.json').read_text())
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
meta = json.loads((ref / 'source-preparation-validation.json').read_text())
assert previous['image_modules_dtb_build_completed'] and tests['actual_functions_tested']
assert tests['baseline_candidate_hardware_effect_signatures_identical']
assert not meta['build_tree_modified']
assert hashlib.sha256((root / 'arch/arm64/boot/Image').read_bytes()).hexdigest() == previous['files']['Image-k144-eud-handoff-private']['sha256']
assert hashlib.sha256((root / 'drivers/tty/serial/eud.c').read_bytes()).hexdigest() == previous['source_sha256']
host = root / 'drivers/gpu/drm/msm/dsi/dsi_host.c'
header = root / 'drivers/gpu/drm/msm/msm_dsi_trace.h'
assert host.read_bytes() == (out / 'dsi-host-before-private.c').read_bytes()
assert not header.exists() and not (out / 'source-diff-before-private.patch').exists()
check = subprocess.run(['perl', str(root / 'scripts/checkpatch.pl'), '--no-signoff',
                        '--ignore', 'COMMIT_MESSAGE', str(ref / 'dsi-observation.patch')],
                       capture_output=True, text=True)
(out / 'checkpatch-private.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0, 'Check private checkpatch diagnostics before applying'
before = subprocess.check_output(['git', '-C', str(root), 'diff', '--binary'])
(out / 'source-diff-before-private.patch').write_bytes(before)
untracked_before = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard']).splitlines()
(out / 'untracked-before-private.json').write_text(json.dumps([p.decode() for p in untracked_before]))
(out / 'config-before-private').write_bytes((root / '.config').read_bytes())
host.write_bytes((out / 'dsi-host-candidate-private.c').read_bytes())
header.write_bytes((ref / 'msm_dsi_trace.h').read_bytes())

def split_diff(data):
    return {block.split(b'\n', 1)[0]: block for block in re.split(rb'(?m)(?=^diff --git )', data) if block}

a = split_diff(before)
b = split_diff(subprocess.check_output(['git', '-C', str(root), 'diff', '--binary']))
key = b'diff --git a/drivers/gpu/drm/msm/dsi/dsi_host.c b/drivers/gpu/drm/msm/dsi/dsi_host.c'
assert set(a) | {key} == set(b)
assert all(a[name] == b[name] for name in a if name != key)
untracked_after = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard']).splitlines()
assert set(untracked_after) == set(untracked_before) | {b'drivers/gpu/drm/msm/msm_dsi_trace.h'}
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
meta['build_tree_modified'] = True
(ref / 'source-preparation-validation.json').write_text(json.dumps(meta, indent=2) + '\n')
report = dict(stage=145, baseline_source_stage=144, only_changed_existing_source='drivers/gpu/drm/msm/dsi/dsi_host.c',
              only_added_source='drivers/gpu/drm/msm/msm_dsi_trace.h',
              full_git_diff_outside_dsi_host_byte_identical=True, untracked_scope_exact=True,
              eud_handoff144_preserved=True, slimbus139_dma140_gpu_charger_preserved=True,
              config_unchanged=True, no_new_mmio_reads_writes_or_printk=True,
              actual_function_cases=24, checkpatch_code_errors=0, checkpatch_code_warnings=0,
              candidate_source_sha256=meta['candidate_source_sha256'],
              trace_header_sha256=meta['trace_header_sha256'], built=False, deployed=False, goal_complete=False)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_ONLY_DSI_OBSERVATION_SOURCE_APPLIED_24_ACTUAL_FUNCTION_CASES_VERIFIED', flush=True)
assert shutil.disk_usage('/mnt/e').free > 1024**3
env = os.environ.copy()
env['PATH'] = '/home/cy122/.cargo/bin:' + env['PATH']
env['RUSTUP_HOME'] = '/home/cy122/.rustup'
env['KBUILD_BUILD_VERSION'] = '145'
base = ['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
        'LD=aarch64-linux-gnu-ld --no-keep-memory']

def constrain_build():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))

def make(name, args):
    log = out / (name + '-build-private.log')
    assert not log.exists()
    with log.open('wb') as stream:
        run = subprocess.run(base + args, cwd=root, env=env, stdout=stream,
                             stderr=subprocess.STDOUT, preexec_fn=constrain_build)
    assert run.returncode == 0, 'Check private build diagnostics: ' + name
    print('K145_' + name.upper() + '_BUILD_EXIT0', flush=True)
    return log

objects = make('dsi-object', ['W=1', '-j2', 'drivers/gpu/drm/msm/dsi/dsi_host.o'])
assert not re.search(r'\b(?:warning|error):', objects.read_text())
make('dsi-image', ['-j2', 'Image', 'modules', 'qcom/sm8150-samurai.dtb'])
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
assert hashlib.sha256(host.read_bytes()).hexdigest() == meta['candidate_source_sha256']
assert hashlib.sha256(header.read_bytes()).hexdigest() == meta['trace_header_sha256']
assert hashlib.sha256((root / 'drivers/tty/serial/eud.c').read_bytes()).hexdigest() == previous['source_sha256']
files = {}
for relative, name in [('arch/arm64/boot/Image', 'Image-k145-dsi-observation-private'),
                       ('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'sm8150-samurai-k145-private.dtb'),
                       ('System.map', 'System-k145-private.map')]:
    target = out / name
    assert not target.exists()
    shutil.copyfile(root / relative, target)
    files[name] = dict(bytes=target.stat().st_size, sha256=hashlib.sha256(target.read_bytes()).hexdigest())
assert files['sm8150-samurai-k145-private.dtb']['sha256'] == '97501daa5639223c018a19c120bce1dbcf45f60abcd404c406c4ee67821d6aa8'
nm = subprocess.check_output(['aarch64-linux-gnu-nm', str(root / 'vmlinux')], text=True)
assert all('__tracepoint_' + name in nm for name in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work'])
build = dict(stage=145, source_sha256=meta['candidate_source_sha256'],
             trace_header_sha256=meta['trace_header_sha256'], image_modules_dtb_build_completed=True,
             dsi_w1_warnings=0, actual_function_cases=24, eud144_actual_function_cases=26,
             reduced_memory_linker=True, address_space_cap_gib=3, dtb_matches132=True,
             three_tracepoints_in_vmlinux=True, module_objects=len(list(root.rglob('*.ko'))),
             files=files, deployed=False, display_accepted=False, gpu_accepted=False,
             charging_accepted=False, real_host_f1_receipt_verified=False, goal_complete=False)
(ref / 'build-validation.json').write_text(json.dumps(build, indent=2) + '\n')
meta['built'] = True
(ref / 'source-preparation-validation.json').write_text(json.dumps(meta, indent=2) + '\n')
print('K145_IMAGE_MODULES_DTB_AND_THREE_TRACEPOINTS_BUILD_COMPLETE_NOT_DEPLOYED', flush=True)
