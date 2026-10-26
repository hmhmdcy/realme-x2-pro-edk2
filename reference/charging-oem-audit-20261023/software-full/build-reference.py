"""Compile the exact cached OEM function bodies, with harmless host stubs."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parent
cache = Path('E:/edk2-samurai-out/kernel83')
prefix = 'realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--'
policy = cache / (prefix + 'drivers--power--oppo--oplus_charger.c')
gauge = cache / (prefix + 'drivers--power--oppo--gauge_ic--oplus_bq27541.c')
dts = cache / (prefix + 'arch--arm64--boot--dts--19781--pm8150b.dtsi')
header = Path('E:/edk2-samurai-out/kernel85/official-oplus_bq27541.h')
source = policy.read_text()
clean_dts = re.sub(r'/\*.*?\*/|//[^\n]*', '', dts.read_text(), flags=re.S)
values = {k: int(v) for k, v in re.findall(r'qcom,([\w-]+)\s*=\s*<(\d+)>', clean_dts)}
fields = ('temp_normal_vfloat_mv', 'temp_cold_vfloat_mv', 'temp_little_cold_vfloat_mv',
          'temp_cool_vfloat_mv', 'temp_little_cool_vfloat_mv', 'temp_warm_vfloat_mv',
          'cold_vfloat_sw_limit', 'little_cold_vfloat_sw_limit', 'cool_vfloat_sw_limit',
          'little_cool_vfloat_sw_limit', 'normal_vfloat_sw_limit', 'warm_vfloat_sw_limit',
          'non_standard_vfloat_sw_limit', 'short_c_bat_vfloat_sw_limit',
          'non_standard_vfloat_mv', 'short_c_bat_vfloat_mv', 'normal_vterm_hw_inc',
          'non_normal_vterm_hw_inc', 'iterm_ma', 'recharge_mv')
limits = {field: values['recharge-mv' if field == 'recharge_mv' else field] for field in fields}
(root / 'reference-limits.inc').write_bytes(''.join(f'.{k} = {v},\n' for k, v in limits.items()).encode())
band_names = ('cold', 'little_cold', 'cool', 'little_cool', 'normal', 'warm')
boundaries = [-values['cold_bat_decidegc'], values['little_cold_bat_decidegc'],
              values['cool_bat_decidegc'], values['little_cool_bat_decidegc'],
              values['normal_bat_decidegc'], values['warm_bat_decidegc'], values['hot_bat_decidegc']]
bands = []
for i, band in enumerate(band_names):
    cv = values[f'temp_{band}_vfloat_mv'] * 1000
    offset = 300000 if band == 'cold' else 200000 if band == 'little_cold' else 100000
    bands.append({'name': band, 'low_decic': boundaries[i], 'high_decic_exclusive': boundaries[i + 1],
                  'oem_cv_uv': cv, 'sw_full_uv_strict_above': values[f'{band}_vfloat_sw_limit'] * 1000,
                  'hw_full_uv_inclusive': cv + values['normal_vterm_hw_inc' if band == 'normal' else 'non_normal_vterm_hw_inc'] * 1000,
                  'band_ovp_uv': values[f'{band}_vfloat_over_sw_limit'] * 1000,
                  'recharge_offset_uv': offset, 'oem_recharge_uv_inclusive': cv - offset})
(root / 'reference-profile.json').write_text(json.dumps({'bands': bands, 'term_current_ua': limits['iterm_ma'] * 1000,
    'tick_seconds': 5, 'sw_charging_samples': 6, 'sw_noncharging_samples': 11,
    'hw_full_samples': 4, 'recharge_samples': 6, 'max_cycle_seconds': values['max_chg_time_sec'],
    'current_word_register': '0x0c', 'average_current_word_register': '0x14',
    'gauge_current_positive_means': 'charging'}, indent=2) + '\n')
names = ('oplus_chg_get_float_voltage', 'oplus_chg_check_sw_full',
         'oplus_chg_check_hw_full', 'oplus_chg_check_rechg_status', 'oplus_chg_full_action')
parts, functions = [], {}
for name in names:
    start = source.index('static ', source.index(name) - 20)
    assert source[start:source.index('{', start)].find(name) >= 0
    end = source.index('\n}', source.index('{', start)) + 2
    body = source[start:end]
    functions[name] = {'first_line': source[:start].count('\n') + 1,
                       'last_line': source[:end].count('\n') + 1,
                       'body_sha256_lf': hashlib.sha256(body.encode()).hexdigest()}
    parts.append(body)
gauge_source = gauge.read_text()
name = 'bq27541_get_average_current'
start = gauge_source.index('static int ' + name)
end = gauge_source.index('\n}', gauge_source.index('{', start)) + 2
body = gauge_source[start:end]
functions[name] = {'source': 'gauge', 'first_line': gauge_source[:start].count('\n') + 1,
                   'last_line': gauge_source[:end].count('\n') + 1,
                   'body_sha256_lf': hashlib.sha256(body.encode()).hexdigest()}
parts.append(body)
for macro in ('#define FULL_COUNTS_SW\t\t5', '#define FULL_COUNTS_HW\t\t4',
              '#define D_RECHGING_CNT\t5'):
    assert macro in source, macro
generated = '/* Exact pinned OEM function bodies; host-only audit fixture. */\n' + '\n\n'.join(parts) + '\n'
(root / 'reference-functions.c').write_bytes(generated.encode())
linux_root = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/software-full'
command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11', '-g',
           '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer', linux_root + '/test-reference.c',
           '-o', linux_root + '/test-reference']
build = subprocess.run(command, text=True, capture_output=True)
assert build.returncode == 0, build.stdout + build.stderr
run = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--',
                      linux_root + '/test-reference'], text=True, capture_output=True)
assert run.returncode == 0, run.stdout + run.stderr
report = json.loads(run.stdout)
report.update({
    'repository': 'https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',
    'commit': '23172a1571bd91156032cc9fef16284a82b63d2c',
    'functions': functions,
    'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (policy, gauge, dts, header, root / 'reference-functions.c', root / 'reference-limits.inc', root / 'test-reference.c')},
    'command': command,
    'stderr': run.stderr,
    'scope': 'Exact OEM SW/HW full and recharge functions with host-only stubs; no physical or production integration acceptance',
    'phone_accessed': False,
    'production_source_modified': False,
})
(root / 'reference-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
