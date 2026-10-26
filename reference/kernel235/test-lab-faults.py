"""Compile actual callbacks with a register-bank/failure model and sanitizers."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
out = P / 'lab-fault-tests-r3'
out.mkdir(mode=0o700)
source = (R / 'qcom-pm8008-imx319-lab.c').read_text()
header = (R / 'qcom-pm8008-imx319-lab.h').read_text()
defines = '\n'.join(l for l in (header + source).splitlines() if l.startswith('#define PM8008_'))
functions = source[source.index('static int pm8008_lab_valid'):source.index('static const struct regulator_ops')]
cleanup = source[source.index('static void pm8008_lab_cleanup'):source.index('/* Reject extra outputs')]
prefix = (R / 'lab-fault-harness-prefix.c').read_text()
main = (R / 'lab-fault-harness-main.c').read_text()
body = prefix + '\n' + defines + '\n' + functions + cleanup + main
path = out / 'actual-callbacks.c'
path.write_text(body)
binary = out / 'actual-callbacks'
compile = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
                          '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path), '-o', str(binary)], capture_output=True)
(out / 'compile-private.log').write_bytes(compile.stdout + compile.stderr)
assert compile.returncode == 0, compile.stderr.decode()[-1800:]
run = subprocess.run([str(binary)], capture_output=True)
(out / 'run-private.log').write_bytes(run.stdout + run.stderr)
assert run.returncode == 0 and not run.stderr, run.stderr.decode()[-1800:]
report = json.loads(run.stdout)
assert report['passed'] and report['cases'] > 400
report.update(stage=235, actual_callbacks_extracted=True, asan_ubsan_passed=True,
              source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              regmap_api_failures_and_partial_write_outcomes_modeled=True,
              persistent_failure_preserves_uncertain_attempted_mask=True,
              p_reset_isolation_and_balancing_after_vdig_failure=True,
              failed_reset_is_not_retried_or_reported_as_off=True,
              real_kernel_core_registration_and_concurrency_not_modeled=True,
              no_phone_operation=True)
(R / 'lab-fault-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
