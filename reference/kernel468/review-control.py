"""Compile finite host checks with the two actual sensor entry points.

Does not build a kernel/module, bind an SDK, change a candidate, or use a device.
Provider stubs are bounded models of inspected numeric-control API semantics.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel468')
s = importlib.util.spec_from_file_location('storage284', HERE.parent/'kernel284/storage.py')
guard = importlib.util.module_from_spec(s)
s.loader.exec_module(guard)
build = guard.mounted_build()
tree = build.parent/'source354'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function(text, name):
    match = re.search(r'\b'+re.escape(name)+r'\(', text)
    assert match, name
    start = text.rfind('static ', 0, match.start())
    begin = text.index('{', match.end())
    level, end = 1, begin+1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]+'\n'


candidate = PRIVATE/'candidate/drivers/media/i2c/s5k3m5.c'
baseline = PRIVATE/'baseline/drivers/media/i2c/s5k3m5.c'
if not baseline.exists():
    baseline = tree/'drivers/media/i2c/s5k3m5.c'
assert sha(candidate) == '88251268b2c10e15116e717511da206e71da35ab359abb8ca80f747c44f2070b'
assert sha(baseline) == 'f0f715826d96521266315f42e6fd9f4a08d1de2695226deecb06fa7c529e1745'
c = candidate.read_text()
modes = re.search(r's5k3m5_clock19_modes\[\] = (\{.*?\n\});', c, re.S).group(1)
modes = re.sub(r'\.reg_list\s*=\s*\{[^}]*\},?', '', modes)
modes = 'static const struct s5k3m5_mode review_modes[] = '+modes+';\n'
legacy = re.search(r's5k3m5_supported_modes\[\] = (\{.*?\n\});', c, re.S).group(1)
legacy = re.sub(r'\.reg_list\s*=\s*\{[^}]*\},?', '', legacy)
modes += 'static const struct s5k3m5_mode legacy_modes[] = '+legacy+';\n'
names = ['s5k3m5_update_pad_format', 's5k3m5_set_ctrl', 's5k3m5_set_pad_format']
constants = '\n'.join(line for line in c.splitlines() if line.startswith('#define') and
    any(token in line for token in ['S5K3M5_EXPOSURE_', 'S5K3M5_REG_AGAIN',
        'S5K3M5_REG_EXPOSURE', 'S5K3M5_REG_VTS', 'S5K3M5_REG_TEST_PATTERN', 'S5K3M5_VTS_MAX']))+'\n'
out = PRIVATE/'finite-control'
out.mkdir(mode=0o700, exist_ok=True)
results = []
for label, path in [('baseline', baseline), ('candidate', candidate)]:
    text = path.read_text()
    extracted = ''.join(function(text, name) for name in names)
    source = out/(label+'.c')
    source.write_text((HERE/'control-harness-prefix.c').read_text()+constants+modes+
                      extracted+(HERE/'control-harness-tests.c').read_text())
    binary = out/label
    cmd = ['gcc', '-std=gnu11', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
           '-Wno-unused-function', '-Wno-unused-variable', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer']
    if label == 'baseline':
        cmd.append('-DREVIEW_BASELINE')
    compile_result = subprocess.run(cmd+[str(source), '-o', str(binary)], text=True,
                                    capture_output=True, timeout=60)
    (out/(label+'-compile.log')).write_text(compile_result.stdout+compile_result.stderr)
    assert compile_result.returncode == 0, compile_result.stderr
    run = subprocess.run([str(binary)], text=True, capture_output=True, timeout=30)
    (out/(label+'-run.log')).write_text(run.stdout+run.stderr)
    assert run.returncode == 0, run.stdout+run.stderr
    results.append(dict(label=label, input_sha256=sha(path),
                        extracted_functions_sha256=hashlib.sha256(extracted.encode()).hexdigest(),
                        host_source_sha256=sha(source), host_binary_sha256=sha(binary),
                        compile_returncode=compile_result.returncode, returncode=run.returncode,
                        result=json.loads(run.stdout)))
report = dict(stage=468, candidate_sha256=sha(candidate), harness_inputs=[dict(
    path=p.name, sha256=sha(p)) for p in [Path(__file__), HERE/'control-harness-prefix.c',
    HERE/'control-harness-tests.c']], compiler=subprocess.check_output(['gcc','--version'], text=True).splitlines()[0],
    results=results, sanitizers=['address', 'undefined'],
    providers='Finite numeric-control range/cache model, held-lock assertion, PM and CCI stubs',
    baseline_mode_descriptors='Candidate descriptors supplied to baseline callbacks; baseline did not expose mode2',
    copied_kernel_core=False, actual_sensor_entry_points_extracted=True,
    actual_kernel_concurrency_test=False, actual_stream_on_executed=False,
    sensor_mode_table_programming_verified=False, sdk_bound=False, phone_accessed=False,
    candidate_modified=False, passed=True)
(HERE/'format-control-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
