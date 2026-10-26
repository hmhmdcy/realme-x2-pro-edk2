"""Build both sources through external M= without rewriting canonical outputs."""
from pathlib import Path
import importlib.util
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time

REF = Path(__file__).resolve().parent
revision = sys.argv[1] if len(sys.argv) == 2 else 'r1'
assert re.fullmatch(r'r[1-9][0-9]*', revision)
spec = importlib.util.spec_from_file_location('prepare227', REF / 'prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
before = json.loads((p.PRIVATE / 'kernel-before-private.json').read_text())
assert p.snapshot() == before
lock = json.loads((REF / 'fastrpc-source-validation.json').read_text())
assert p.digest((p.BUILD / 'candidate/fastrpc.c').read_bytes()) == lock['candidate_source_sha256']


def run(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))


env = dict(os.environ, KBUILD_BUILD_VERSION='183',
           PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')
check_args = [str(p.KERNEL / 'scripts/checkpatch.pl'), '--no-tree', '--strict', '--no-signoff']
patch = str(REF / 'fastrpc-publication-lifetime.patch')
cp = subprocess.run([*check_args, patch], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(p.PRIVATE / (revision + '-checkpatch-unfiltered-private.log')).write_bytes(cp.stdout)
assert cp.stdout.count(b"Deprecated use of 'idr_init'") == 1
filtered = subprocess.run([*check_args, '--ignore', 'DEPRECATED_API', patch], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(p.PRIVATE / (revision + '-checkpatch-private.log')).write_bytes(filtered.stdout)
assert filtered.returncode == 0, 'Check the private checkpatch log'
symbols = {line.split()[1] for line in (p.KERNEL / 'Module.symvers').read_text().splitlines()}
old_vm = run(['modinfo', '-F', 'vermagic', str(p.PRIVATE / 'fastrpc-before-private.ko')])
results = {}
names = ('baseline', 'candidate')
if revision != 'r1':
    previous = json.loads((REF / 'fastrpc-build-validation.json').read_text())
    assert previous['results']['baseline']['source_sha256'] == lock['source_before_sha256']
    results['baseline'] = previous['results']['baseline']
    names = ('candidate',)
for name in names:
    folder = p.BUILD / name
    log = p.PRIVATE / ((revision + '-' if revision != 'r1' else '') + name + '-external-build-private.log')
    assert not log.exists(), 'Use the existing build session instead of replaying it'
    started = time.monotonic()
    try:
        with log.open('xb') as output:
            subprocess.run(['make', '-C', str(p.KERNEL), 'M=' + str(folder),
                            'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                            'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j3', 'modules'],
                           env=env, stdout=output, stderr=subprocess.STDOUT,
                           preexec_fn=limit, check=True)
    finally:
        current = p.snapshot()
        (p.PRIVATE / (name + '-kernel-after-private.json')).write_text(json.dumps(current, indent=2) + '\n')
        assert current == before, 'Canonical kernel state changed; inspect before proceeding'
    elapsed = time.monotonic() - started
    assert not re.findall(r'^.*\b(?:warning|error):.*$', log.read_text(), re.M)
    module = p.PRIVATE / ('fastrpc227-' + name + '-private.ko')
    shutil.copyfile(folder / 'fastrpc.ko', module)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(module)], check=True)
    vm = run(['modinfo', '-F', 'vermagic', str(module)])
    assert vm == old_vm
    undefined = run(['aarch64-linux-gnu-nm', '-u', str(module)])
    imports = {line.split()[-1] for line in undefined.splitlines() if line.strip()}
    assert imports <= symbols
    assert 'AArch64' in run(['readelf', '-h', str(module)])
    results[name] = {'source_sha256': p.digest((folder / 'fastrpc.c').read_bytes()),
                     'module_sha256': p.digest(module.read_bytes()), 'module_bytes': module.stat().st_size,
                     'seconds_including_preservation_check': round(elapsed, 3),
                     'imports': sorted(imports), 'vermagic': vm, 'w1_warnings': 0,
                     'modpost_passed': True, 'arm64': True, 'canonical_unchanged': True}
report = {'stage': 227, 'build_revision': revision, 'external_M_build': True, 'kernel_build': 183,
          'canonical_preserved_files': len(before) - 2, 'results': results,
          'checkpatch_errors': 0, 'checkpatch_unrelated_moved_idr_api_warning': 1,
          'checkpatch_after_narrow_exclusion': 0, 'no_fabricated_signoff': True,
          'import_additions': sorted(set(results['candidate']['imports']) - set(results['baseline']['imports'])),
          'runtime_deployed': False, 'phone_changes': False}
(REF / 'fastrpc-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((p.PRIVATE / 'current-work-private.json').read_text())
state.update(state='baseline and candidate external builds terminal; host behavior checks pending',
             active_build_session=None)
(p.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'results'}))
print(json.dumps({n: {k: v for k, v in v.items() if k != 'imports'} for n, v in results.items()}))
