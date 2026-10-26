"""Prove the existing actual-callback harness detects three deleted guards."""
from pathlib import Path
import hashlib
import json
import resource
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
positive = json.loads((R / 'lab-fault-validation.json').read_text())
assert positive['source_sha256'] == hashlib.sha256((R / 'qcom-pm8008-imx319-lab.c').read_bytes()).hexdigest()
body = (P / 'lab-fault-tests-r3/actual-callbacks.c').read_text()
out = P / 'lab-negative-controls-r2'
out.mkdir(mode=0o700)
variants = {
    'missing_enable_fault_guard': ('if (s->fault || s->removing || !s->ready)', 'if (s->removing || !s->ready)'),
    'missing_failed_enable_clear': ('cleanup_ret = pm8008_lab_clear(s, rail->index);', 'cleanup_ret = 0;'),
    'missing_cleanup_mask_audit': ('if ((mask & ~s->mask) || mask != s->enabled_mask ||\n\t    s->attempted_mask != s->enabled_mask)', 'if (false)'),
}
results = {}
for name, (old, new) in variants.items():
    assert body.count(old) == 1
    path = out / (name + '.c')
    path.write_text(body.replace(old, new))
    binary = out / name
    result = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
                             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path), '-o', str(binary)], capture_output=True)
    (out / (name + '-compile-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0
    def limit():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(binary)], capture_output=True, preexec_fn=limit)
    (out / (name + '-run-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode != 0 and b'Assertion' in result.stderr
    results[name] = dict(compiled=True, rejected_by_actual_callback_counterexample=True)
report = dict(stage=235, negative_controls=results, source_product_not_modified=True,
              positive_actual_callback_cases=positive['cases'])
(R / 'lab-negative-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
