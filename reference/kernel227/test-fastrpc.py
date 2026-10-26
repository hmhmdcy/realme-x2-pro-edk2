"""Fault injection against actual extracted probe/open/callback functions."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

REF = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare227', REF / 'prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
revision = sys.argv[1] if len(sys.argv) == 2 else 'r1'
assert re.fullmatch(r'r[1-9][0-9]*', revision)
work = p.BUILD / ('host-tests' if revision == 'r1' else 'host-tests-' + revision)
assert not work.exists(), 'Follow an existing experiment rather than replaying it'
work.mkdir()
template = (REF / 'publication-harness.c').read_text()
build = json.loads((REF / 'fastrpc-build-validation.json').read_text())


def extract(source, pattern, semicolon=False):
    match = re.search(pattern, source, re.M)
    assert match, pattern
    start = match.start()
    brace = source.index('{', match.end())
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    if semicolon:
        assert source[end] == ';'
        end += 1
    return source[start:end]


def sha(data):
    return hashlib.sha256(data.encode()).hexdigest()


extracted = {}
for name in ('baseline', 'candidate'):
    source = (p.BUILD / name / 'fastrpc.c').read_text()
    assert sha(source) == build['results'][name]['source_sha256']
    structs = [extract(source, '^struct ' + n + r'(?= \{)', True) for n in (
        'fastrpc_session_ctx', 'fastrpc_soc_data', 'fastrpc_channel_ctx', 'fastrpc_device', 'fastrpc_user')]
    functions = ['fastrpc_channel_ctx_free', 'fastrpc_channel_ctx_get', 'fastrpc_channel_ctx_put',
                 'fastrpc_session_alloc' + ('_locked' if name == 'candidate' else ''),
                 'fastrpc_session_free', 'fastrpc_device_open', 'fastrpc_device_register',
                 'fastrpc_get_domain_id']
    if name == 'candidate':
        functions.append('fastrpc_channel_ctx_release')
    functions += ['fastrpc_rpmsg_probe', 'fastrpc_rpmsg_callback']
    bodies = {n: extract(source, r'^static[^;{]*\b' + n + r'\([^;{]*\)\s*(?=\{)') for n in functions}
    combined = template.replace('/* @DRIVER_STRUCTS@ */', '\n\n'.join(structs))
    combined = combined.replace('/* @DRIVER_FUNCTIONS@ */', '\n\n'.join(bodies.values()))
    file = work / (name + '.c')
    file.write_text(combined)
    args = ['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-sign-compare',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread',
            str(file), '-o', str(work / name)]
    if name == 'baseline':
        args.insert(1, '-DBASELINE')
    compile_run = subprocess.run(args, capture_output=True)
    (p.PRIVATE / (revision + '-' + name + '-host-compile-private.log')).write_bytes(compile_run.stdout + compile_run.stderr)
    assert compile_run.returncode == 0, 'See host compile log'
    extracted[name] = {'source_sha256': sha(source), 'functions': {n: sha(b) for n, b in bodies.items()},
                       'generated_harness_sha256': sha(combined)}

env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
negative = subprocess.run([str(work / 'baseline')], capture_output=True, env=env, timeout=10)
(p.PRIVATE / (revision + '-baseline-negative-control-private.log')).write_bytes(negative.stdout + negative.stderr)
assert negative.returncode == 86 and b'get of uninitialized channel kref' in negative.stderr
cases = ['single-node', 'dual-node', 'first-misc-failure', 'second-misc-failure',
         'partial-child-failure', 'no-session', 'owner-action-failure',
         'dma-setup-failure', 'scm-setup-failure', 'callback-held-across-probe-failure', 'allocation-failure']
env['ASAN_OPTIONS'] = 'detect_leaks=1:abort_on_error=1'
results = {}
for index, name in enumerate(cases):
    result = subprocess.run([str(work / 'candidate'), str(index)], capture_output=True, env=env, timeout=10)
    (p.PRIVATE / (revision + '-host-' + name + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, name + ': see private host-test log'
    assert b'PASS' in result.stdout and not result.stderr
    results[name] = {'exit_code': 0, 'asan_ubsan_findings': 0, 'output': result.stdout.decode().strip()}
assert p.snapshot() == json.loads((p.PRIVATE / 'kernel-before-private.json').read_text())
report = {'stage': 227, 'harness_revision': revision, 'baseline_negative_control_exit': 86,
          'baseline_detected_uninitialized_kref': True, 'candidate_cases': results,
          'actual_functions_extracted_unchanged': extracted, 'asan_ubsan': True,
          'harness_scope': 'probe publication/open admission/failure unwind/owner lifetime, mocked kernel APIs',
          'does_not_validate': ['real DMA', 'DSP restart', 'active-client removal', 'physical sensors'],
          'canonical_unchanged': True, 'runtime_deployed': False, 'phone_changes': False}
(REF / 'fastrpc-host-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('actual_functions_extracted_unchanged', 'candidate_cases')}))
print(json.dumps({'passed_cases': len(results), 'cases': list(results)}))
