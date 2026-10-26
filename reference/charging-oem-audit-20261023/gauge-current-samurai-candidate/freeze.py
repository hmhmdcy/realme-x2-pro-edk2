"""Bind finished offline artifacts; no test rerun or source/build/device action."""
from pathlib import Path
import hashlib, json

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda name: json.loads((HERE / name).read_text())
source, test, build = read('source-result.json'), read('test-result.json'), read('build-result.json')
assert source['passed'] and test['passed'] and build['passed']
assert source['default_enabled'] is False
assert source['candidate_sha256'] == sha(HERE / 'bq27xxx_battery.c') == build['source_sha256']
assert source['baseline_sha256'] == sha(HERE / 'baseline-bq27xxx_battery.c')
assert build['test_receipt_sha256'] == sha(HERE / 'test-result.json')
for name, digest in test['files'].items():
    assert sha(HERE / name) == digest, name
assert test['group_count'] == 6 and test['actual_functions'] == 9
assert test['original_function_differential_cases'] == 36
assert build['shared_inputs_unchanged'] and not build['diagnostic_lines']
assert not build['Image_or_ko_linked'] and not build['installed']
assert read('caller-audit.json')['passed'] and read('supplement-callers.json')['passed']
primary = ['README.md', 'bq27xxx_battery.c', 'samurai-current.patch', 'source-result.json',
           'test-result.json', 'build-result.json', 'caller-audit.json', 'supplement-callers.json']
result = dict(passed=True, frozen=True, scope='default-off native samurai gauge CURRENT_NOW/STATUS instant 0c and CURRENT_AVG 14 only',
              files={name: sha(HERE / name) for name in primary},
              default_enabled=False, actual_functions=9, targeted_test_groups=6,
              default_actual_differential_cases=36, asan_ubsan=True, W1_diagnostic_lines=[],
              object_private=build['object_private'], object_sha256=build['object_sha256'],
              source_commit=source['source_commit'], baseline_sha256=source['baseline_sha256'],
              shared_source_configuration_unchanged=True, Image_or_ko_linked=False,
              installed=False, latency_benefit_measured=False,
              old_charging_protection_suites_rerun=False,
              phone_accessed=False, SSH_invoked=False, USB_invoked=False, SDK_invoked=False, Git_invoked=False)
(HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
delivery = dict(schema=1, frozen=True,
                files={p.name: sha(p) for p in sorted(HERE.iterdir())
                       if p.is_file() and p.name != 'delivery.json'})
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n')
print(json.dumps(dict(result_sha256=sha(HERE / 'result.json'),
                      delivery_sha256=sha(HERE / 'delivery.json'),
                      patch_sha256=sha(HERE / 'samurai-current.patch'),
                      build_receipt_sha256=sha(HERE / 'build-result.json')), indent=2))
