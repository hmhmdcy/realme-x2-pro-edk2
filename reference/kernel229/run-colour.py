"""Measure32 real RGB frames, retain aggregates only, then restore hardware state."""
from pathlib import Path
import hashlib
import json
import host

ref = Path(__file__).resolve().parent
build = json.loads((ref / 'colour-probe-build-validation.json').read_text())
binary = host.PRIVATE / 'daylight-colour-probe229'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == build['binary_sha256']
host.upload(binary, '/run/samurai-camera229-probes/daylight-colour-probe')
check = "from pathlib import Path;import hashlib,os;p=Path('/run/samurai-camera229-probes/daylight-colour-probe');assert hashlib.sha256(p.read_bytes()).hexdigest()==%r;os.chmod(p,0o755);print('New RAM-only colour probe hash verified')" % build['binary_sha256']
result = host.ssh('python3 -', input=check.encode(), timeout=15)
(host.PRIVATE / 'colour-probe-upload-private.log').write_bytes(result.stdout + result.stderr)
code = (ref / 'native-daylight-baseline.py').read_text()
assert code.count("'k229-capture-daylight-baseline-'") == 1
code = code.replace("'k229-capture-daylight-baseline-'", "'k229-capture-daylight-colour-'")
code = code.replace('/run/samurai-camera229-probes/native-mode-probe', '/run/samurai-camera229-probes/daylight-colour-probe')
code = code.replace('process.communicate(timeout=25)', 'process.communicate(timeout=45)')
(ref / 'native-colour-runner.py').write_text(code)
result = host.ssh('python3 - rgb 0 2296 1728 1 system', input=code.encode(), timeout=95)
(host.PRIVATE / 'daylight-colour-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'daylight-colour-native-validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert report['program_exit'] == 0 and len(report['frames']) == 32
assert report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored'] and report['camera_devices_suspended']
assert report['taint'] == 4096 and not any(report['fault_delta'].values())
frames = report['frames']
summary = dict(stage=229, frame_count=32, actual_format='RGB888', last8=frames[-8:],
               all_frames_nonzero=all(not f['all_zero'] for f in frames),
               mean_range=[min(f['mean'] for f in frames), max(f['mean'] for f in frames)],
               differing_channel_fraction_range=[min(f['differing_channels_fraction'] for f in frames), max(f['differing_channels_fraction'] for f in frames)],
               exposure_us_range=[min(f['exposure_us'] for f in frames), max(f['exposure_us'] for f in frames)],
               analogue_gain_range=[min(f['analogue_gain'] for f in frames), max(f['analogue_gain'] for f in frames)],
               controls_graph_formats_pm_restored=True, fault_increments=report['fault_delta'],
               scene_images_saved=False, lighting='user reports daylight', colour_accuracy_not_yet_calibrated=True)
(ref / 'daylight-colour-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
