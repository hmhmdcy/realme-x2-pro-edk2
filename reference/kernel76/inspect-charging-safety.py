"""Inspect local upstream/vendor sources and the archived stock DT, read-only."""
from pathlib import Path
import hashlib, json, re, subprocess, tarfile

OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
OUT.mkdir(parents=True, exist_ok=True)
KERNEL = Path('/home/cy122/x2pro-linux/linux')
VENDOR = '/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
COMMIT = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'

def vendor(path):
    return subprocess.check_output(['git', '--git-dir=' + VENDOR, 'cat-file', '-p', COMMIT + ':' + path]).decode(errors='replace')

def function(text, name):
    # Remove comment/string contents while preserving byte positions for braces.
    clean = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)
    match = re.search(r'^[^\n;]*\b' + re.escape(name) + r'\s*\([^;{}]*?\)\s*\{', clean, re.M)
    if not match:
        return ''
    start, pos = match.start(), match.end()
    count = 1
    while count and pos < len(text):
        count += (clean[pos] == '{') - (clean[pos] == '}')
        pos += 1
    return text[start:pos]

result = {'vendor_commit': COMMIT, 'upstream': {}, 'vendor': {}}
for path, names in {
    'drivers/power/supply/bq27xxx_battery.c': ['bq27xxx_battery_settings', 'bq27xxx_battery_setup'],
    'drivers/power/supply/bq27xxx_battery_i2c.c': ['bq27xxx_battery_i2c_probe'],
}.items():
    text = (KERNEL / path).read_text()
    result['upstream'][path] = {name: function(text, name) for name in names}
for path, names in {
    'drivers/power/oppo/charger_ic/oppo_mp2650.c': ['mp2650_hardware_init', 'mp2650_parse_dt', 'mp2650_driver_probe', 'mp2650_charging_enable', 'mp2650_otg_enable'],
    'drivers/power/oppo/gauge_ic/oppo_bq27541.c': ['bq27541_parse_dt', 'bq27541_battery_probe'],
}.items():
    text = vendor(path)
    result['vendor'][path] = {name: function(text, name) for name in names}

archive = '/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar'
with tarfile.open(archive) as tar:
    props = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
nodes = sorted({p.rsplit('/', 1)[0] for p in props if p.endswith('/compatible') and re.search(b'charger|oppo.chg|vooc|da9313|short-ic|stm8s|bq27541|mp2650|smb5|smb1390|fg-gen4', props[p], re.I)})
nodes += sorted({p.rsplit('/', 1)[0] for p in props if re.search(r'(?:oppo|oplus).{0,5}(?:chg|vooc).{0,30}/', p, re.I)} - set(nodes))
result['live_nodes'] = nodes
result['live_policy_candidate_paths'] = sorted(p for p in props if re.search(r'batt_num|chargeric|chg_ctrl|temp.*(?:normal|warm|cold)|float.*voltage|(?:oppo|oplus|vooc)', p, re.I))
paths = subprocess.check_output(['git', '--git-dir=' + VENDOR, 'ls-tree', '-r', '--name-only', COMMIT, 'arch/arm64/boot/dts/19781']).decode().splitlines()
result['vendor_policy_candidate_files'] = [p for p in paths if re.search(r'charg|batt|oppo|pm8150|mtp|190', p, re.I)]
policy = {}
for node in nodes:
    if not re.search(r'qpnp-smb5|stm8s_fastcg|oppo.?charg|oppo.?chg|oplus.?chg|vooc', node, re.I):
        continue
    for path, raw in props.items():
        if path.rsplit('/', 1)[0] != node or re.search(r'key|sha1|auth', path, re.I):
            continue
        if path.endswith(('/name', '/phandle', '/linux,phandle')):
            continue
        policy[path] = {'hex': raw.hex(), 'u32': [int.from_bytes(raw[i:i+4], 'big') for i in range(0, len(raw), 4)] if len(raw) % 4 == 0 else None}
result['live_policy'] = policy
source_paths = subprocess.check_output(['git', '--git-dir=' + VENDOR, 'ls-tree', '-r', '--name-only', COMMIT, 'drivers/power']).decode().splitlines()
result['stock_charger_source_paths'] = [p for p in source_paths if re.search(r'qpnp.*smb5|oppo_charger\.[ch]$|oppo_vooc\.[ch]$', p)]
result['mp2650_callers'] = subprocess.check_output(['git', '--git-dir=' + VENDOR, 'grep', '-n', '-e', 'mp2650_chg_ops', '-e', 'vbatt_num == 2', COMMIT, '--', 'drivers/power']).decode().splitlines()[:45]
for path in ['arch/arm64/boot/dts/19781/pm8150b.dtsi', 'drivers/power/oppo/oppo_charger.c']:
    text = vendor(path)
    (OUT / ('stock--' + path.replace('/', '--'))).write_text(text)
handles = [0x205, 0x51b, 0x531, 0x532, 0x533]
result['live_pin_handles'] = {}
for path, raw in props.items():
    if path.endswith(('/phandle', '/linux,phandle')) and len(raw) == 4 and int.from_bytes(raw, 'big') in handles:
        node = path.rsplit('/', 1)[0]
        result['live_pin_handles'][hex(int.from_bytes(raw, 'big'))] = {p: v.hex() for p, v in props.items() if p.startswith(node + '/') and (int.from_bytes(raw, 'big') != 0x51b or p.rsplit('/', 1)[0] == node)}
config = (KERNEL / '.config').read_text()
result['power_config'] = [l for l in config.splitlines() if re.search(r'BATTERY_BQ27|CHARGER_MP|QCOM_BATTMGR|QCOM_SMB', l)]
result['mainline_mp_sources'] = [p.name for p in (KERNEL / 'drivers/power/supply').glob('*mp26*')]
(OUT / 'local-safety-inspection.json').write_text(json.dumps(result, indent=2) + '\n')
show = {k:v for k,v in result.items() if k not in ('upstream','vendor','live_policy_candidate_paths','vendor_policy_candidate_files','live_policy')}
show['live_pin_handles'] = list(result['live_pin_handles'])
show['selected_live_policy'] = {p:v for p,v in policy.items() if re.search(r'vbatt_num|temp_bat_(cold|hot)|temp_normal.*(?:current|vfloat)|non_standard|iterm|usb.*current|dcp.*current|chg.*timeout|vooc_project', p, re.I)}
print(json.dumps(show, indent=2))
