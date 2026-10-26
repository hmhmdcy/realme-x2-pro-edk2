from pathlib import Path
import hashlib
import json
import re
import subprocess

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel139')
out = Path('/mnt/e/edk2-samurai-out/kernel139')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert not (out / 'host-fault-injection-validation.json').exists()

def function(s, name):
    hit = re.search(r'^(?:static (?:inline )?)?(?:u32 \*|void |int |bool )' + name + r'\(', s, re.M)
    assert hit, name
    start = hit.start()
    a = s.index('{', start)
    depth = 1
    b = a + 1
    while depth:
        depth += (s[b] == '{') - (s[b] == '}')
        b += 1
    return s[start:b] + '\n'

header = (k / 'drivers/slimbus/slimbus.h').read_text()
ngd = (k / 'drivers/slimbus/qcom-ngd-ctrl.c').read_text()
messaging = (k / 'drivers/slimbus/messaging.c').read_text()
macros = []
for source in [(k / 'include/linux/slimbus.h').read_text(), header, ngd]:
    lines = source.splitlines(True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'#define\s+(?:SLIM_\w+|QCOM_SLIM_NGD_DESC_NUM)\b', line):
            macro = line
            while lines[i].rstrip().endswith('\\'):
                i += 1
                macro += lines[i]
            macros.append(macro)
        i += 1
common = (ref / 'fault-injection-stubs.h').read_text() + '\n' + ''.join(macros)
common += function(header, 'slim_tid_txn') + function(header, 'slim_ec_txn')
names = ['qcom_slim_ngd_tx_msg_get', 'qcom_slim_ngd_tx_msg_dma_cb', 'qcom_slim_ngd_tx_msg_post', 'qcom_slim_ngd_xfer_msg']
records = {}
for label, ngd_source, messaging_source in [
    ('baseline132', (out / 'qcom-ngd-ctrl.c.132-before-private').read_text(), (out / 'messaging.c.132-before-private').read_text()),
    ('candidate139', ngd, messaging)]:
    extracted = ''.join(function(ngd_source, name) for name in names) + function(messaging_source, 'slim_do_transfer')
    text = common + extracted + (ref / 'fault-injection-main.c').read_text()
    source = out / (label + '-fault-injection-private.c')
    source.write_text(text)
    exe = out / (label + '-fault-injection-private')
    compile_result = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Wno-unused-parameter', '-Werror', '-g', '-fsanitize=address,undefined', str(source), '-o', str(exe)], capture_output=True)
    (out / (label + '-host-build-private.log')).write_bytes(compile_result.stdout + compile_result.stderr)
    assert compile_result.returncode == 0, label + ' compile failed'
    result = subprocess.run([str(exe)], capture_output=True)
    (out / (label + '-host-run-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == (2 if label == 'baseline132' else 0), label + ' test failed'
    assert result.stderr == b'', 'sanitizer diagnostics'
    records[label] = json.loads(result.stdout)
    records[label]['extracted_functions_sha256'] = hashlib.sha256(extracted.encode()).hexdigest()
assert records['baseline132']['dma_failures'] == 31 and records['baseline132']['ring_exhaustions'] == 69
assert all(records['candidate139']['cases'])
report = dict(stage=139, actual_driver_functions_extracted_verbatim=True,
              primitive_dma_tid_pm_stubs=True, physical_dma_fault_not_injected=True,
              address_and_undefined_sanitizers_clean=True, cases=12,
              baseline_ring_leak_reproduced=True, recovery_after_100_failures_pass=True,
              earlier_inflight_slot_preserved=True, direct_user_tid_owner_preserved=True,
              results=records, device_runtime_not_yet_validated=True, goal_complete=False)
for folder in [ref, out]:
    (folder / 'host-fault-injection-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
