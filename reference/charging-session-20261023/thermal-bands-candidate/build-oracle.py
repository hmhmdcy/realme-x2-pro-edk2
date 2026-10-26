"""Extract and execute pinned OEM temperature/Full bodies, entirely offline."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
CACHE = Path('E:/edk2-samurai-out/kernel83')
PREFIX = 'realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--'
SOURCE = CACHE / (PREFIX + 'drivers--power--oppo--oplus_charger.c')
DTS = CACHE / (PREFIX + 'arch--arm64--boot--dts--19781--pm8150b.dtsi')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == '6cfb97b4367afe25094f3f342db4c9cce7982a22708371bc08ac6ed8bc9aa2d4'
assert hashlib.sha256(DTS.read_bytes()).hexdigest() == '43d554879e68bb9b7795d7fb37530dfe6a5ce6cc6aae42514057e757079140c8'
source = SOURCE.read_text()
names = ['battery_temp_anti_shake_handle', 'oplus_chg_check_tbatt_is_good',
         'battery_temp_normal_anti_shake_handle', 'oplus_chg_check_tbatt_normal_status',
         'oplus_chg_get_float_voltage', 'oplus_chg_check_sw_full',
         'oplus_chg_check_hw_full', 'oplus_chg_check_rechg_status']
bodies = []; functions = {}
for name in names:
    match = re.search(r'^static (?:void|bool|int) ' + name + r'\([^;{]*\)\s*\{', source, re.M)
    assert match, name
    end = source.index('\n}', match.end()) + 2
    body = source[match.start():end]
    bodies.append(body)
    functions[name] = dict(first_line=source[:match.start()].count('\n') + 1,
                           last_line=source[:end].count('\n') + 1,
                           sha256_lf=hashlib.sha256(body.encode()).hexdigest())
text = '\n\n'.join(bodies) + '\n'
(HERE / 'oracle-functions.inc').write_bytes(text.encode())
clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', DTS.read_text(), flags=re.S)
values = {k: int(v) for k, v in re.findall(r'qcom,([\w-]+)\s*=\s*<(\d+)>', clean)}
fields = sorted(set(re.findall(r'chip->limits\.(\w+)', text)))
limits = {name: values.get('recharge-mv' if name == 'recharge_mv' else name, 0) for name in fields}
limits['cold_bat_decidegc'] = -values['cold_bat_decidegc']
limits['removed_bat_decidegc'] = -values['removed_bat_decidegc']
limits['normal_phase6_bat_decidegc'] = values.get('normal_phase6_bat_decidegc', 420)
(HERE / 'oracle-limits.inc').write_text(''.join('.' + k + '=' + str(v) + ',\n' for k, v in limits.items()))
(HERE / 'oracle-limit-fields.inc').write_text(''.join('int ' + name + ';\n' for name in fields))
linux = '/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/thermal-bands-candidate'
command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer', linux + '/test-oracle.c', '-o', linux + '/test-oracle']
subprocess.run(command, check=True)
result = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', linux + '/test-oracle'], capture_output=True, text=True)
assert result.returncode == 0, result.stdout + result.stderr
report = json.loads(result.stdout)
report.update(repository='https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',
              commit='23172a1571bd91156032cc9fef16284a82b63d2c', functions=functions, command=command,
              source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), dts_sha256=hashlib.sha256(DTS.read_bytes()).hexdigest(),
              scope='exact OEM temperature/Full bodies with harmless host stubs; before candidate implementation',
              phone_accessed=False, sdk_accessed=False, shared_source_modified=False)
(HERE / 'oracle-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
