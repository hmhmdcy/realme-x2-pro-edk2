"""Run only cached kernel/UPower/Phosh decision functions on synthetic input."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parent
cache = root.parent.parent / 'charging-ui-audit-20261023'
files = {name: cache / name for name in ('kernel-bq27xxx_battery.c',
    'upower-up-device-supply.c', 'upower-up-device-supply-battery.c', 'phosh-battery-manager.c')}
parts = {}

def function(name, signature):
    text = files[name].read_text()
    start = text.index(signature)
    end = text.index('\n}', text.index('{', start)) + 2
    return text, start, end

def save(label, text, start, end, source):
    value = text[start:end] + '\n'
    (root / label).write_bytes(value.encode())
    parts[label] = {'source': str(files[source]), 'first_line': text[:start].count('\n') + 1,
                    'last_line': text[:end].count('\n') + 1,
                    'sha256_lf': hashlib.sha256(value.encode()).hexdigest()}

for label, signature in (('kernel-full.inc', 'static bool bq27xxx_battery_is_full('),
                         ('kernel-status.inc', 'static int bq27xxx_battery_current_and_status(')):
    text, start, end = function('kernel-bq27xxx_battery.c', signature)
    save(label, text, start, end, 'kernel-bq27xxx_battery.c')
kernel = files['kernel-bq27xxx_battery.c'].read_text()
macros = ('BQ27000_FLAG_FC', 'BQ27000_FLAG_CHGS', 'BQ27XXX_FLAG_FC', 'BQ27Z561_FLAG_FC',
          'BQ27XXX_RS', 'BQ27XXX_CURRENT_CONSTANT', 'BQ27XXX_O_ZERO', 'BQ27Z561_O_BITS')
selected = []
for macro in macros:
    selected.append(re.search(r'^#define ' + macro + r'\b[^\n]*', kernel, re.M).group(0))
assert '[BQ27XXX_REG_AI] = 0x14' in kernel[kernel.index('bq28z610_regs['):kernel.index('bq28z610_regs[') + 900]
assert '[BQ28Z610]  = BQ27XXX_DATA(bq28z610,  0         , BQ27Z561_O_BITS)' in kernel
(root / 'kernel-macros.inc').write_bytes(('\n'.join(selected) + '\n').encode())
text, start, end = function('upower-up-device-supply.c', 'UpDeviceState\nup_device_supply_get_state (')
save('upower-state.inc', text, start, end, 'upower-up-device-supply.c')
text = files['upower-up-device-supply-battery.c'].read_text()
start = text.index('\tvalues.state = up_device_supply_get_state (native);')
end = text.index('\n\tvalues.temperature', start)
save('upower-override.inc', text, start, end, 'upower-up-device-supply-battery.c')
text = files['phosh-battery-manager.c'].read_text()
start = text.index('  is_charging = state ==')
end = text.index('\n  if (g_strcmp0', start)
save('phosh-icon.inc', text, start, end, 'phosh-battery-manager.c')

linux_root = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/icon-semantics'
command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11', '-g',
           '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer', linux_root + '/test-icons.c', '-lm',
           '-o', linux_root + '/test-icons']
build = subprocess.run(command, text=True, capture_output=True)
assert build.returncode == 0, build.stdout + build.stderr
run = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', linux_root + '/test-icons'],
                     text=True, capture_output=True)
assert run.returncode == 0, run.stdout + run.stderr
report = json.loads(run.stdout)
report.update({'source_files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},
    'fragments': parts, 'command': command, 'stderr': run.stderr,
    'sanitizers': ['ASan', 'UBSan'], 'phone_accessed': False, 'production_modified': False,
    'actual_display_aggregation_executed': False, 'screen_render_latency_measured': False,
    'scope': 'Cached actual kernel functions, UPower source-state/negative-current branch and Phosh icon selection branch; synthetic inputs, not event timing or root-cause proof'})
(root / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
