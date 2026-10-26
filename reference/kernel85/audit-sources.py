"""Offline Android R/cyborg chemistry and final archived DT audit.

Full vendor source/header files and Android DT archive remain private.
Publishes selected definitions, hashes and boolean presence only.
"""
from pathlib import Path
import hashlib
import json
import re
import tarfile

OUT = Path('/mnt/e/edk2-samurai-out/kernel85')
PREV = Path('/mnt/e/edk2-samurai-out/kernel83')
ARCHIVE = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
sha = lambda data: hashlib.sha256(data).hexdigest()
expected_archive_sha = 'e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b'
assert sha(ARCHIVE.read_bytes()) == expected_archive_sha
with tarfile.open(ARCHIVE) as tar:
    files = {m.name.removeprefix('./'): tar.extractfile(m).read() for m in tar if m.isfile()}
node = 'soc/i2c@0xc94000/bq27541-battery@55'
assert files[node + '/reg'] == bytes.fromhex('00000055')
assert files[node + '/qcom,batt_bq28z610'] == b''
key = 'qcom,bq28z610_need_balancing'
archive_properties = sorted(name.removeprefix(node + '/') for name in files if name.startswith(node + '/'))
archived_balancing_bool = node + '/' + key in files

def block(source, needle):
    pos = source.index(needle)
    start = source.index('{', pos)
    depth, end = 1, start + 1
    while depth:
        depth += int(source[end] == '{') - int(source[end] == '}')
        end += 1
    return source[start + 1:end - 1]

def uncomments(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)

manifest_rows = {}
for filename in ['charging-source-manifest.json', 'board-source-manifest.json', 'board-includes-manifest.json', 'cyborg-dt-layout.json']:
    for row in json.loads((PREV / filename).read_text())['files']:
        manifest_rows[(row.get('repo', 'cyborgdc2000/kernel_realme_sm8150'), row['path'])] = row
source_results = []
for group, directory in [('official', '19781'), ('cyborg', 'qcom')]:
    header_manifest = json.loads((OUT / (group + '-gauge-header-manifest.json')).read_text())
    repo = header_manifest['repo']
    header = (OUT / (group + '-oplus_bq27541.h')).read_bytes()
    assert sha(header) == header_manifest['sha256'] == '58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e'
    assert len(header) == header_manifest['bytes']
    definitions = {}
    wanted = ['DEVICE_TYPE_BQ28Z610', 'Bq28Z610_REG_TI', 'Bq28Z610_REG_AI',
              'BQ28Z610_DEVICE_CHEMISTRY_EN_ADDR', 'BQ28Z610_DEVICE_CHEMISTRY_CMD',
              'BQ28Z610_DEVICE_CHEMISTRY_ADDR', 'BQ28Z610_DEVICE_CHEMISTRY_SIZE',
              'BQ28Z610_OPERATION_STATUS_CMD', 'BQ28Z610_BALANCING_CONFIG_BIT']
    for name in wanted:
        definitions[name] = re.search(r'^#define\s+' + name + r'\s+([^\s/]+)', header.decode(), re.M)[1]
    assert int(definitions['DEVICE_TYPE_BQ28Z610'], 0) == 0xffa5
    assert int(definitions['BQ28Z610_DEVICE_CHEMISTRY_CMD'], 0) == 0x4b
    assert definitions['BQ28Z610_BALANCING_CONFIG_BIT'] == 'BIT(28)'
    paths = ['drivers/power/oppo/gauge_ic/oplus_bq27541.c',
             'arch/arm64/boot/dts/' + directory + '/sm8150-pmic-overlay.dtsi',
             'drivers/power/oppo/charger_ic/oplus_short_ic.c']
    contents = {}
    for path in paths:
        raw = (PREV / (repo.replace('/', '--') + '--' + path.replace('/', '--'))).read_bytes()
        row = manifest_rows[(repo, path)]
        assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
        contents[path] = raw.decode()
    gauge = contents[paths[0]]
    assert sha(gauge.encode()) == '0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87'
    assert 'chip->bq28z610_need_balancing = of_property_read_bool(node, "' + key + '");' in gauge
    assert 'if (gauge_ic->bq28z610_need_balancing)' in gauge
    assert 'chip->cmd_addr.reg_ai = Bq28Z610_REG_TI;' in gauge
    chemistry = block(gauge, 'static int bq28z610_get_device_chemistry(')
    assert 'usleep_range(1000, 1000);' in chemistry
    assert 'BQ28Z610_DEVICE_CHEMISTRY_CMD' in chemistry
    assert 'BQ28Z610_DEVICE_CHEMISTRY_ADDR' in chemistry
    assert 'return DEVICE_CHEMISTRY_LION;' in chemistry
    body = block(block(uncomments(contents[paths[1]]), '&qupv3_se15_i2c'), 'bq27541-battery@55')
    source_balancing_bool = key + ';' in body
    short = contents[paths[2]]
    assert sha(short.encode()) == 'fea6f381755e0491ce4f3667cca427ec2b03ab1b1e817f294cdbb2906d72fadf'
    otp = block(uncomments(short), 'bool oplus_short_ic_otp_check(')
    absent = block(otp, 'if(chip->b_oplus_short_ic_exist == false)')
    unready = block(otp, 'if(chip == NULL)')
    assert 'return true;' in absent and 'return true;' in unready
    assert 'chip->b_oplus_short_ic_exist = false;' in short
    source_results.append({
        'repo': repo, 'commit': header_manifest['commit'], 'header': header_manifest,
        'selected_definitions': definitions,
        'gauge_source_sha256': sha(gauge.encode()),
        'DT_source_path': paths[1], 'DT_source_sha256': manifest_rows[(repo, paths[1])]['sha256'],
        'source_gauge_node_balancing_bool_present': source_balancing_bool,
        'archived_gauge_node_balancing_bool_present': archived_balancing_bool,
        'OEM_temperature_compensation_branch_selected_by_archived_DT': archived_balancing_bool,
        'OEM_current_selector_for_legacy_FFA5': '0x0c (instantaneous)',
        'short_IC_source_sha256': sha(short.encode()),
        'short_IC_OTP_check_returns_true_when_unready_or_nonexistent': True,
        'short_IC_source_behavior_is_independent_protection_proof': False,
    })
assert source_results[0]['source_gauge_node_balancing_bool_present'] == source_results[1]['source_gauge_node_balancing_bool_present'] == archived_balancing_bool
mainline_path = Path('/home/cy122/x2pro-linux/linux/drivers/power/supply/bq27xxx_battery.c')
mainline_raw = mainline_path.read_bytes()
mainline_table = block(mainline_raw.decode(), 'bq28z610_regs[BQ27XXX_REG_MAX] =')
assert '[BQ27XXX_REG_AI] = 0x14,' in mainline_table
result = {
    'audit': 'PASS', 'kind': 'pinned source and final archived Android DT, no device interaction',
    'archive_sha256': expected_archive_sha, 'archive_gauge_node': node,
    'archived_property_names_only': archive_properties, 'sources': source_results,
    'legacy_FFA5_is_defined_in_both_references': True,
    'extended_2719_exact_variant_verified': False,
    'chemical_label_is_a_unique_chip_or_calibration_ID': False,
    'thermal_calibration_or_independent_protection_verified': False,
    'mainline_local_source': {'path': 'drivers/power/supply/bq27xxx_battery.c',
                             'sha256': sha(mainline_raw), 'current_now_selector': '0x14 (average)',
                             'source_unchanged_this_session': True},
    'scope': 'Archived handset Android DT and these pinned references; no assertion about other boards or actual historical build commit.',
}
(OUT / 'source-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: both pinned headers and gauge/DT sources; final archived DT balancing bool =', archived_balancing_bool)
