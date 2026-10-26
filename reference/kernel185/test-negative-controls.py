from pathlib import Path
import json
import subprocess

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel185')
original = (out / 'qca-pulse-host-private.c').read_text()
changes = {
    'drops_nuls_outside_pulse': ('test_bit(QCA_POWER_PULSE, &qca->flags) &&', 'true &&'),
    'drops_partial_payload': ('!qca->rx_skb && !hu->padding)', '!hu->padding)'),
    'reports_short_consumption': ('\n\treturn received;\n}', '\n\treturn count;\n}'),
    'accepts_zero_byte_write': ('if (ret != 1)', 'if (ret < 0)'),
    'leaves_flow_disabled': ('restore_flow:\n\thci_uart_set_flow_control(hu, false);', 'restore_flow:'),
}
report = []
for name, (before, after) in changes.items():
    assert original.count(before) == 1
    source = out / (name + '-negative-private.c')
    binary = out / (name + '-negative-private.bin')
    source.write_text(original.replace(before, after))
    with (out / (name + '-compile-private.log')).open('wb') as log:
        subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-sign-compare', '-fsanitize=address,undefined', str(source), '-o', str(binary)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    result = subprocess.run([str(binary)], capture_output=True)
    (out / (name + '-runtime-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode != 0 and b'Assertion' in result.stderr
    report.append({'mutation': name, 'expected_failure_detected': True})
data = json.loads((ref / 'host-tests-validation.json').read_text())
data['negative_controls'] = report
data['all_negative_controls_detected'] = True
(ref / 'host-tests-validation.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'negative_controls': len(report), 'all_detected': True}))
