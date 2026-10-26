"""Bind source, target module and successful/failed host receipts without reruns."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel455')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda name: json.loads((HERE / name).read_text())
source_sha = sha(HERE / 'bu64253.c')
build = read('module-build-validation.json')
host = read('lifetime-c-validation.json')
assert build['passed'] and host['passed']
assert source_sha == build['source_sha256'] == host['source_sha256']
module = PRIVATE / ('bu64253-lifetime-r3-build' + str(build['attempt']) + '.ko')
assert sha(module) == build['module_sha256']
imports = json.loads((PRIVATE / 'module-imports-private.json').read_text())
assert 'try_module_get' in imports and 'module_put' in imports and '__module_get' not in imports
prior = json.loads((HERE.parent / 'kernel453/module-build-validation.json').read_text())
assert sha(HERE.parent / 'kernel453/bu64253.c') == prior['driver_source_sha256']
assert sha(PRIVATE.parent / 'kernel453/bu64253-intree-r2.ko') == prior['module_sha256']
logs = {}
for p in PRIVATE.glob('*-private.log'):
    logs[p.name] = dict(bytes=p.stat().st_size, sha256=sha(p))
first = (PRIVATE / 'lifetime-c-compile-r1-private.log').read_text()
assert 'puts' in first and 'redeclared' in first
report = dict(stage=455, candidate='BU64253 lifetime r3', source_sha256=source_sha,
              module_sha256=build['module_sha256'], source_module_and_host_receipts_consistent=True,
              module_imports_try_module_get_and_module_put_but_not___module_get=True,
              host_first_attempt_compile_failed=True,
              host_first_failure='stub counter named puts collided with stdio puts; only stub renamed',
              host_second_attempt_passed=True,
              host_third_attempt_added_exact_valid_init_byte_assertions_without_source_change=True,
              retained_quarantine_objects_and_power_pins=2, logs=logs,
              original_453_source_and_module_unchanged=True,
              core_0064_or_image_updated=False, kernel_framework_or_hardware_tested=False,
              sdk_or_phone_accessed=False, files_stable_for_parent_mirror=True, passed=True)
(HERE / 'final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='logs'},indent=2))
