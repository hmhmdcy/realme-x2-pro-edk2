"""Generate a private source-only sensor-properties candidate. Never builds."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out')
OUT = PRIVATE / 'kernel487'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('guard487p', HERE.parent / 'kernel284/storage.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.mounted_build()
    evidence = json.loads((HERE / 'metadata-evidence-validation.json').read_text())
    assert evidence['passed'] and evidence['cases'] == 9
    assert sha(OUT / 'metadata-native-evidence-private.json') == evidence['private_evidence_sha256']
    source = Path(json.loads((HERE.parent / 'kernel473/source-state.json').read_text())['source'])
    relative = Path('src/libcamera/sensor/camera_sensor_properties.cpp')
    original = source / relative
    assert sha(original) == '938ea102ca456b3d853d7bffc18822a2c674dfd76d4c65c4e3c282e13d618b14'
    before = original.read_text()
    assert not any('"' + name + '"' in before for name in ['imx319', 's5k3m5', 's5kgw1'])
    assert '"imx471"' in before
    assert 'in nanometers' in (source / 'src/libcamera/property_ids_core.yaml').read_text()
    imx = '''\t\t{ "imx319", {
\t\t\t.unitCellSize = { 1400, 1400 },
\t\t\t.testPatternModes = {
\t\t\t\t{ controls::draft::TestPatternModeOff, 0 },
\t\t\t\t{ controls::draft::TestPatternModeSolidColor, 1 },
\t\t\t\t{ controls::draft::TestPatternModeColorBars, 2 },
\t\t\t\t{ controls::draft::TestPatternModeColorBarsFadeToGray, 3 },
\t\t\t\t{ controls::draft::TestPatternModePn9, 4 },
\t\t\t},
\t\t\t.sensorDelays = { },
\t\t} },
'''
    samsung = '''\t\t{ "s5k3m5", {
\t\t\t.unitCellSize = { 1000, 1000 },
\t\t\t.testPatternModes = {
\t\t\t\t{ controls::draft::TestPatternModeOff, 0 },
\t\t\t\t{ controls::draft::TestPatternModeSolidColor, 1 },
\t\t\t\t{ controls::draft::TestPatternModeColorBars, 2 },
\t\t\t\t{ controls::draft::TestPatternModeColorBarsFadeToGray, 3 },
\t\t\t\t{ controls::draft::TestPatternModePn9, 4 },
\t\t\t},
\t\t\t.sensorDelays = { },
\t\t} },
\t\t{ "s5kgw1", {
\t\t\t.unitCellSize = { 800, 800 },
\t\t\t.testPatternModes = {
\t\t\t\t{ controls::draft::TestPatternModeOff, 0 },
\t\t\t\t/* V4L2 menu index1 programs register value2. */
\t\t\t\t{ controls::draft::TestPatternModeColorBars, 1 },
\t\t\t\t/* Shade Color Bars (index2) lacks a confirmed standard map. */
\t\t\t},
\t\t\t.sensorDelays = { },
\t\t} },
'''
    after = before.replace('\t\t{ "imx327", {', imx + '\t\t{ "imx327", {', 1)
    after = after.replace('\t\t{ "vd55g1", {', samsung + '\t\t{ "vd55g1", {', 1)
    assert before != after
    patch = HERE / '0001-camera-sensor-add-samurai-model-properties.patch'
    patch.write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='a/' + str(relative), tofile='b/' + str(relative))))
    baseline, candidate = OUT / 'baseline', OUT / 'candidate'
    assert not baseline.exists() and not candidate.exists(), 'Keep an issued candidate immutable'
    (baseline / relative).parent.mkdir(parents=True)
    (baseline / relative).write_text(before)
    shutil.copytree(baseline, candidate)
    process = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch)], cwd=candidate,
                             capture_output=True, text=True, timeout=10)
    (OUT / 'patch-apply-private.log').write_text(process.stdout + process.stderr)
    assert process.returncode == 0 and 'offset' not in process.stdout and 'fuzz' not in process.stdout
    assert (candidate / relative).read_text() == after
    # Removing only the new entries recovers the exact old file, including471.
    assert after.replace(imx, '', 1).replace(samsung, '', 1) == before
    kernel = Path('/mnt/samurai-full282/source354')
    driver_paths = {'s5kgw1': kernel / 'drivers/media/i2c/s5kgw1.c',
                    'imx319': kernel / 'drivers/media/i2c/imx319.c',
                    's5k3m5': PRIVATE / 'kernel468/candidate/drivers/media/i2c/s5k3m5.c',
                    'imx471': kernel / 'drivers/media/i2c/imx471.c'}
    assert sha(driver_paths['s5k3m5']) == '88251268b2c10e15116e717511da206e71da35ab359abb8ca80f747c44f2070b'
    menus = {}
    for name, path in driver_paths.items():
        data = path.read_text()
        menu = re.search(r'static const char \* const ' + name + r'_test_pattern_menu\[\] = \{(.*?)\};', data, re.S)
        assert menu
        labels = re.findall(r'"([^"]+)"', menu[1])
        assert len(labels) == (3 if name == 's5kgw1' else 5)
        assert labels[0] == 'Disabled'
        if name == 's5kgw1':
            assert labels == ['Disabled', 'Color Bars', 'Shade Color Bars']
            assert 's5kgw1_test_pattern_values[] = { 0, 2, 3 }' in data
        else:
            assert 'Solid' in labels[1] and ('Bars' in labels[2] or 'bars' in labels[2]) and ('PN9' in labels[4])
        assert 'v4l2_fwnode_device_parse' in data and 'v4l2_ctrl_new_fwnode_properties' in data
        menus[name] = dict(source_sha256=sha(path), labels=labels)
    # The actual retained boot DTB, not another handset's orientation.
    dtb = PRIVATE / 'kernel468/frozen363-samurai.dtb'
    assert sha(dtb) == 'dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
    nodes = {'s5kgw1': '/soc@0/cci@ac4a000/i2c-bus@0/camera@10',
             'imx319': '/soc@0/cci@ac4a000/i2c-bus@1/camera@10',
             's5k3m5': '/soc@0/cci@ac4b000/i2c-bus@0/camera@2d',
             'imx471': '/soc@0/cci@ac4b000/i2c-bus@1/camera@10'}
    board = {}
    for name, node in nodes.items():
        names = subprocess.check_output(['fdtget', '-p', str(dtb), node], text=True).splitlines()
        assert 'rotation' not in names and 'orientation' in names
        orientation = int(subprocess.check_output(['fdtget', '-t', 'u', str(dtb), node, 'orientation'], text=True))
        assert orientation == (0 if name == 'imx471' else 1)
        board[name] = dict(node=node, orientation=orientation, rotation_present=False, driver_reads_fwnode=True)
    legacy = (source / 'src/libcamera/sensor/camera_sensor_legacy.cpp').read_text()
    assert '.exposureDelay = 2' in legacy and '.gainDelay = 1' in legacy
    assert '(!staticProps_->sensorDelays.exposureDelay' in legacy
    report = dict(stage=487, passed=True, candidate_created=True, patch_sha256=sha(patch),
        baseline_source_sha256=sha(original), candidate_source_sha256=sha(candidate / relative),
        properties_added=['imx319', 's5k3m5', 's5kgw1'], imx471_entry_unchanged=True,
        old_file_exact_after_removing_new_entries=True, patch_zero_fuzz_zero_offset=True,
        pixel_units_from_actual_hal_consumer=True, mapping_uses_v4l2_menu_indices=True,
        driver_test_menus=menus, gw1_shade_index2_not_mapped=True,
        sensor_delays_empty=True, legacy_default_delay_fallback_unchanged=True,
        rotation_metadata=board, retained_dtb_sha256=sha(dtb), rotation_patch_created=False,
        shared_source_unchanged=sha(original) == '938ea102ca456b3d853d7bffc18822a2c674dfd76d4c65c4e3c282e13d618b14',
        no_sdk=True, no_compile=True, no_ssh=True, no_phone=True, hardware_patterns_validated=False,
        source_fixture_checks_only=True)
    (HERE / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, candidate_source_sha256=report['candidate_source_sha256'],
                         test_menus=list(menus), rotation_patch_created=False)))


if __name__ == '__main__':
    main()
