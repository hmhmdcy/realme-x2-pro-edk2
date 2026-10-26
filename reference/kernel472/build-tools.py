"""Build only the two private472 measurement clients against retained461.

No libcamera/IPA build, source changes, device, upload, or client execution.
The only source-tree bind is read-only and is released in finally.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel472')
spec = importlib.util.spec_from_file_location('tools472_storage461', HERE.parent/'kernel461/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mount.mounted_build()
source = storage.candidate()
tree = source/'src/libcamera-v0.7.2'
sdk = storage.SDK
slot = sdk/'work/libcamera'
work = sdk/'private/camss472-tools'
work.mkdir(exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, timeout=120):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def is_mounted():
    return command(['mountpoint', '-q', str(slot)]).returncode == 0


assert not is_mounted(), 'SDK source slot already mounted; do not change another binding'
processes = command(['ps', '-eo', 'pid,args']).stdout.splitlines()
compilers = [line for line in processes if any(token in line for token in
             ['cc1plus', '/cc1 ', '/collect2 ', 'ninja -C', 'meson compile'])]
assert not compilers, compilers
prep = json.loads((HERE/'preparation-validation.json').read_text())
baseline = prep['original_source_sha256']
for name, digest in baseline.items():
    assert sha(HERE.parent/'kernel306'/name) == digest
sources = dict(stepper=PRIVATE/'candidate-control-stepper.c', capture=PRIVATE/'candidate-delay-capture.cpp')
for label, path in sources.items():
    name = 'control-stepper.c' if label == 'stepper' else 'delay-capture.cpp'
    assert sha(path) == prep['candidate_source_sha256'][name]
    shutil.copyfile(path, work/path.name)

runtime_paths = [tree/'output/src/libcamera/libcamera.so.0.7.2',
    tree/'output/src/libcamera/base/libcamera-base.so.0.7.2',
    tree/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
    tree/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
    tree/'output/src/libcamera/proxy/worker/camss_ipa_proxy']
runtime_before = {str(p): sha(p) for p in runtime_paths}
proof461 = json.loads((HERE.parent/'kernel461/build-validation.json').read_text())
expected = {row['name']: row['sha256'] for row in proof461['runtime_files']}
for path in runtime_paths:
    if path.name in expected:
        assert sha(path) == expected[path.name], path.name
headers = sorted((tree/'include/libcamera').rglob('*.h')) + sorted((tree/'output/include/libcamera').rglob('*.h'))
headers_before = {str(p.relative_to(tree)): sha(p) for p in headers}
state_paths = [p for p in [tree/'output/.ninja_log', tree/'output/.ninja_deps', tree/'output/build.ninja'] if p.exists()]
state_before = {str(p): sha(p) for p in state_paths}
version_header = (tree/'output/include/libcamera/version.h').read_text()
assert [int(re.search(r'#define LIBCAMERA_VERSION_'+part+r'\s+(\d+)', version_header).group(1))
        for part in ['MAJOR', 'MINOR', 'PATCH']] == [0, 7, 2]
capture_source = sources['capture'].read_text()
assert capture_source.index('camera->configure(config.get())') < capture_source.index('stepper.start(argv[2])')
stepper_source = sources['stepper'].read_text()
assert stepper_source.index('if(verify_mode2(sensor))') < stepper_source.index('STEPPER_READY')
assert stepper_source.count('if(verify_mode2(sensor))') == 2

T = '/work/libcamera/src/libcamera-v0.7.2'
W = '/private/camss472-tools'
commands = [
    ('stepper', ['gcc', '-std=gnu11', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
       '-Wno-misleading-indentation', W+'/candidate-control-stepper.c', '-o', W+'/control-stepper-mode2-aarch64']),
    ('capture', ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
       '-I'+T+'/include', '-I'+T+'/output/include', W+'/candidate-delay-capture.cpp',
       '-L'+T+'/output/src/libcamera', '-L'+T+'/output/src/libcamera/base',
       '-Wl,-rpath-link,'+T+'/output/src/libcamera/base', '-lcamera', '-lcamera-base',
       '-pthread', '-o', W+'/delay-capture-mode2-aarch64']),
]
rows = []
bind_created = False
started = time.monotonic()
mount_before = command(['findmnt', '-J', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS']).stdout
(PRIVATE/'tools-mounts-before-private.json').write_text(mount_before)
try:
    subprocess.run(['mount', '--bind', str(source), str(slot)], check=True, capture_output=True)
    bind_created = True
    subprocess.run(['mount', '-o', 'remount,bind,ro', str(slot)], check=True, capture_output=True)
    binding = command(['findmnt', '--mountpoint', str(slot), '-J', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
    assert binding.returncode == 0
    bound = json.loads(binding.stdout)['filesystems'][0]
    assert 'ro' in bound['options'].split(',')
    compiler_versions = {}
    for compiler in ['gcc', 'g++']:
        result = command(['chroot', str(sdk), compiler, '--version'], timeout=20)
        assert result.returncode == 0, result.stderr
        compiler_versions[compiler] = result.stdout.splitlines()[0]
    for label, args in commands:
        result = command(['chroot', str(sdk), *args])
        (PRIVATE/(label+'-build-private.log')).write_text(result.stdout+result.stderr)
        rows.append(dict(label=label, command=['chroot', str(sdk), *args], returncode=result.returncode))
        (PRIVATE/'tools-build-attempt-private.json').write_text(json.dumps(rows, indent=2)+'\n')
        assert result.returncode == 0, result.stderr
        output = work/('control-stepper-mode2-aarch64' if label == 'stepper' else 'delay-capture-mode2-aarch64')
        target = PRIVATE/output.name
        shutil.copyfile(output, target)
        target.chmod(0o700)
        elf = command(['readelf', '-h', '-l', '-d', str(target)])
        assert elf.returncode == 0 and 'AArch64' in elf.stdout
        (PRIVATE/(label+'-elf-private.txt')).write_text(elf.stdout)
        rows[-1].update(path=str(target), bytes=target.stat().st_size, sha256=sha(target),
            source_sha256=sha(sources[label]), aarch64=True,
            static=label == 'stepper', interpreter=next((line.strip() for line in elf.stdout.splitlines()
                if 'Requesting program interpreter' in line), None),
            needed=[line.strip() for line in elf.stdout.splitlines() if '(NEEDED)' in line])
finally:
    if bind_created:
        subprocess.run(['umount', str(slot)], check=True, capture_output=True)
assert not is_mounted()
assert {str(p): sha(p) for p in runtime_paths} == runtime_before
assert {str(p.relative_to(tree)): sha(p) for p in headers} == headers_before
assert {str(p): sha(p) for p in state_paths} == state_before
for name, digest in baseline.items():
    assert sha(HERE.parent/'kernel306'/name) == digest
report = dict(stage=472, scope='two measurement clients only', passed=True,
    script_sha256=sha(Path(__file__)), sdk=str(sdk), source=str(tree), version='0.7.2',
    wsl_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    sdk_source_slot_unbound_before=True, exclusive_compiler_check_empty=True,
    read_only_source_binding=bound, sdk_bind_unmounted=True, compiler_versions=compiler_versions,
    tools=rows, headers_sha256=hashlib.sha256(json.dumps(headers_before, sort_keys=True).encode()).hexdigest(),
    header_files=len(headers), runtime_files=[dict(path=p, sha256=digest) for p,digest in runtime_before.items()],
    headers_and_runtime_unchanged=True, ninja_state_unchanged=True, frozen306_sources_unchanged=True,
    candidate_sources_unchanged=True, capture_configure_before_stepper=True,
    mode_guard_after_configure_before_start_and_at_sof0=True,
    original_project_c_warning_exception='-Wno-misleading-indentation, retained for original compact C style',
    clients_executed=False, uploaded=False, phone_accessed=False, shared_source_changed=False,
    libcamera_or_ipa_rebuilt=False, physical_delay_measured=False, seconds=round(time.monotonic()-started,3))
(HERE/'tools-build-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
