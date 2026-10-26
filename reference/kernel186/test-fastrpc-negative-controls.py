from pathlib import Path
import json
import subprocess

private = Path('/mnt/e/edk2-samurai-out/kernel186')
ref = Path(__file__).resolve().parent
original = (private / 'actual-fastrpc-pool-test-private.c').read_text()
mutations = [
    ('remove_leaves_pool_assigned', '\tfastrpc_unassign_reserved_pool(&rpdev->dev, cctx);', ''),
    ('failed_probe_leaves_pool_assigned', '\tfastrpc_unassign_reserved_pool(rdev, data);', ''),
    ('failed_reclaim_discards_ownership', '\tif (ret) {\n\t\tdev_err(dev, "failed to reclaim reserved pool:',
        '\tif (ret) {\n\t\tcctx->reserved_pool_size = 0;\n\t\tdev_err(dev, "failed to reclaim reserved pool:'),
    ('failed_reclaim_claims_success', '\t\tdev_err(dev, "failed to reclaim reserved pool: %d\\n", ret);\n\t\treturn ret;',
        '\t\tdev_err(dev, "failed to reclaim reserved pool: %d\\n", ret);\n\t\treturn 0;'),
]
report = []
for name, before, after in mutations:
    assert original.count(before) == 1, name
    path = private / ('negative-' + name + '-private.c')
    path.write_text(original.replace(before, after))
    binary = path.with_suffix('')
    p = subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(path), '-o', str(binary)], capture_output=True)
    (private / ('negative-' + name + '-compile-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0
    p = subprocess.run([str(binary)], capture_output=True)
    (private / ('negative-' + name + '-runtime-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode != 0 and b'Assertion' in p.stderr
    report.append({'mutation': name, 'compiled': True, 'expected_runtime_failure_detected': True})
data = json.loads((ref / 'fastrpc-host-tests-validation.json').read_text())
data['negative_controls'] = report
data['all_negative_controls_detected'] = True
(ref / 'fastrpc-host-tests-validation.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'negative_controls': report, 'all_detected_by_runtime_assertions': True}))
