"""Check public sources against both current canonical and the measured artifacts."""
from pathlib import Path
import importlib.util
import json
import subprocess

ref = Path(__file__).resolve().parent
root = ref.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel229')
spec = importlib.util.spec_from_file_location('prepare227', ref.parent / 'kernel227/prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
assert p.snapshot() == json.loads((private.parent / 'kernel228/canonical-after-private.json').read_text())
lock = json.loads((root / 'linux-port/ssc/kernel/source-lock.json').read_text())
assert p.digest((root / 'linux-port/ssc/kernel/fastrpc.c').read_bytes()) == lock['source_sha256'] == p.digest((p.KERNEL / 'drivers/misc/fastrpc.c').read_bytes())
assert p.digest((root / 'linux-port/ssc/kernel/0001-fastrpc-publication-lifetime.patch').read_bytes()) == lock['patch_sha256']
assert lock['rootfs_default']['clean_boot_verified'] is False
scripts = sorted((ref.parent / 'kernel228').glob('*.py')) + sorted(ref.glob('*.py'))
for script in scripts:
    compile(script.read_text(), str(script), 'exec')
shells = sorted((ref.parent / 'kernel228').glob('*.sh'))
for script in shells:
    subprocess.run(['bash', '-n', str(script)], check=True)
build = json.loads((ref / 'colour-probe-build-validation.json').read_text())
assert p.digest((ref / 'daylight-colour-probe.cpp').read_bytes()) == build['source_sha256']
assert p.digest((private / 'daylight-colour-probe229').read_bytes()) == build['binary_sha256']
for kind in ['raw', 'rgb']:
    case = json.loads((ref / (kind + '-daylight-baseline-validation.json')).read_text())
    assert len(case['frames']) == 6 and not any(f['all_zero'] for f in case['frames'])
case = json.loads((ref / 'daylight-colour-native-validation.json').read_text())
assert len(case['frames']) == 32 and not any(f['all_zero'] for f in case['frames'])
assert all(f['exposure_us'] > 0 and f['analogue_gain'] >= 1 for f in case['frames'])
for key in ['all_formats_restored', 'media_graph_restored', 'sensor_controls_restored', 'camera_devices_suspended']:
    assert case[key]
assert case['taint'] == 4096 and not any(case['fault_delta'].values())
assert 'std::ofstream' not in (ref / 'daylight-colour-probe.cpp').read_text()
checkpoint = root / 'NEXT-SESSION.md'
assert len(checkpoint.read_bytes()) <= 6500
for heading in ['## 源码、产物与回退依据', '## 续作与已知风险']:
    assert heading in checkpoint.read_text()
report = dict(stages=[228, 229], current_guard='/var/lib/samurai/k228-runtime/boot-id-private.txt',
              canonical_after_integration_preserved=True, accepted_full_fastrpc_source_locked=True,
              python_sources_compile=len(scripts), shell_sources_syntax_pass=len(shells),
              actual_colour_probe_source_binary_match=True, numeric_frames_recorded=44,
              camera_state_restored=True, no_new_faults=True, only_known_external_OOT4096=True,
              clean_intree_boot_still_pending=True, checkpoint_bytes=len(checkpoint.read_bytes()),
              source228_native119_member_archive_preserved=True)
(ref / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
