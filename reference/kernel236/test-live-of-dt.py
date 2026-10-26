"""Test actual DT validation with the live OF-generated metadata and rejections."""
from pathlib import Path
import hashlib
import json
import resource
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel236')
out = P / 'live-of-dt-tests-r1'
out.mkdir(mode=0o700)
source = (R / 'qcom-pm8008-imx319-lab.c').read_text()
extract = lambda text: text[text.index('static int pm8008_lab_validate_dt('):text.index('static int pm8008_lab_probe(')]
function = extract(source)
old = extract((R.parent / 'kernel235/qcom-pm8008-imx319-lab.c').read_text())
prefix = (R / 'lab-dt-prefix.c').read_text()
main = (R / 'lab-dt-main.c').read_text()
variants = dict(actual=function, old_rejects_live_name=old,
                ignore_name_value=function.replace('memcmp(property->value, expected, 5)', '(expected == NULL)'),
                allow_unknown_properties=function.replace('if (strcmp(name, "regulator-name")', 'if (false && strcmp(name, "regulator-name")'))
assert all(variants[name] != function for name in variants if name != 'actual')
def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
results = {}
for name, value in variants.items():
    path = out / (name + '.c')
    path.write_text(prefix + value + main)
    binary = path.with_suffix('')
    build = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path), '-o', str(binary)], capture_output=True)
    (out / (name + '-compile-private.log')).write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0, build.stderr.decode()[-2000:]
    run = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
    (out / (name + '-run-private.log')).write_bytes(run.stdout + run.stderr)
    if name == 'actual':
        assert run.returncode == 0 and not run.stderr, run.stderr.decode()[-2000:]
        results[name] = json.loads(run.stdout)
    else:
        assert run.returncode != 0 and b'Assertion' in run.stderr
        results[name] = dict(rejected=True, exit=run.returncode)
report = dict(stage=236, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              actual_validator_extracted=True, live_of_generated_name_included=True, asan_ubsan_passed=True,
              results=results, property_lengths_nul_unknown_rails_voltage_and_refcounts_checked=True,
              real_device_core_and_registration_not_modeled=True, no_phone_operation=True)
(R / 'live-of-dt-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
