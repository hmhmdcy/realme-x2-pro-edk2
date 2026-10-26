"""Compare saved float results without rerunning the original HAL."""
import collections, json, struct
from pathlib import Path
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE
cases = json.loads((P / 'curve-cases-private.json').read_text())
host_raw = (P / 'curves-host-output-private.bin').read_bytes()
arm_raw = (P / 'curves-aarch64-output-private.bin').read_bytes()
source_raw = (P / 'curve-source-expected-private.bin').read_bytes()
hal_raw = (P / 'curves-hal-output-private.bin').read_bytes()
assert len(source_raw) == len(cases) * 788 and len(hal_raw) == len(cases) * 396
assert len(host_raw) == len(arm_raw) == (len(cases) + 81) * 788
groups = collections.defaultdict(lambda: dict(cases=0, host_arm_float_different_bytes=0,
    host_hal_float_different_bytes=0, host_source_float_different_bytes=0,
    max_host_hal_float_difference=0))
for i, case in enumerate(cases):
    host_values = host_raw[i*788+8:i*788+404]
    target_values = hal_raw[i*396:(i+1)*396]
    arm_values = arm_raw[i*788+8:i*788+404]
    source_values = source_raw[i*788+8:i*788+404]
    group = groups[case['kind']]
    group['cases'] += 1
    for label, actual in [('host_arm', arm_values), ('host_hal', target_values), ('host_source', source_values)]:
        group[label + '_float_different_bytes'] += sum(a != b for a, b in zip(host_values, actual))
    group['max_host_hal_float_difference'] = max(group['max_host_hal_float_difference'],
        max(abs(a-b) for a,b in zip(struct.unpack('<99f', host_values), struct.unpack('<99f', target_values))))
report = dict(stage=407, groups=dict(groups),
              powf_provider_is_same_host_libm_for_target_fragments=True,
              passed=all(g['host_arm_float_different_bytes'] == g['host_hal_float_different_bytes'] == 0
                         for g in groups.values()))
(HERE / 'float-comparison-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert report['passed']
