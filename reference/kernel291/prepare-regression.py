"""Reuse the standard four-camera regression after the physical PIX/RDI tests."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;old=ROOT.parent/'kernel290'
for filename in ['native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py']:
 s=(old/filename).read_text().replace('k290-four-camera-regression','k291-four-camera-regression').replace('k290-tools','k291-tools').replace('stage=290','stage=291')
 # Keep the deployed kernel290 boot guard and kernel identity checks.
 s=s.replace('four-camera-launch-private','four-camera291-launch-private').replace('four-camera-poll-private','four-camera291-poll-private')
 target=ROOT/filename;assert not target.exists();target.write_text(s)
s=(old/'final-health.py').read_text()
s=s.replace("assert json.loads((ROOT/'standard-tpg-validation.json').read_text())['actual_frames']==3", "assert json.loads((ROOT/'physical-pixel-validation.json').read_text())['sensor_pattern_color_contract_passed']\nassert json.loads((ROOT/'tele-pixel-validation.json').read_text())['color_contract_passed']")
s=s.replace('stage=290','stage=291').replace('k290-services-verified-private','k291-services-verified-private').replace('k290-work/final-health-private','k291-tools/final-health-private')
s=s.replace('standard_tpg_no_mmio=True','standard_tpg_no_mmio=True,two_physical_csi_sensor_patterns_verified=True,physical_scene_quality_unverified=True')
(ROOT/'final-health.py').write_text(s)
print('Prepared post-PIX/RDI standard regression and final inventory checks.')
