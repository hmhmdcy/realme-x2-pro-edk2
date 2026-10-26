"""Prepare new-boot regressions and preserve all older evidence."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
for name in ['native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py','analyze-sof.py']:
 s=(HERE.parent/'kernel297'/name).read_text().replace('297','298')
 s=s.replace('four-camera295-','four-camera298-').replace('stats-r2-capture','blc-capture')
 (HERE/name).write_text(s)
s=(HERE.parent/'kernel297/final-health.py').read_text().replace('297','298')
a=s.index("assert json.loads((ROOT/'four-camera-regression-validation.json')");b=s.index("code=r'''",a)
s=s[:a]+'''assert json.loads((ROOT/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((ROOT/'blc-pixel-validation.json').read_text())['all_phase_color_contracts_passed']
assert json.loads((ROOT/'sof-association-validation.json').read_text())['shared_sof_contract_passed']
assert json.loads((ROOT/'blc-frame-association-validation.json').read_text())['exact_frame_association_proven']
'''+s[b:]
needle="prior296_inventory=json.loads((r/'k296-deployment/module-inventory-private.json').read_text())"
pos=s.index('\n',s.index('assert len(prior296_inventory)',s.index(needle)))
s=s[:pos]+'''
prior297=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k297+')
prior297_inventory=json.loads((r/'k297-deployment/module-inventory-private.json').read_text())
assert len(prior297_inventory)==778 and prior297_inventory=={str(p.relative_to(prior297)):sha(p) for p in prior297.rglob('*.ko')}
'''+s[pos:]
s=s.replace('old296_778_modules_preserved=True,','old297_778_modules_preserved=True,old296_778_modules_preserved=True,')
s=s.replace('physical_scene_exposure_response_verified=True,','physical_scene_exposure_response_verified_on_prior297=True,')
s=s.replace('standard_wb_params_verified=True,','standard_wb_params_verified=True,standard_equal_channel_black_subtraction_verified=True,sensor_dark_calibration_pending=True,')
(HERE/'final-health.py').write_text(s)
for p in HERE.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
print('Prepared current-boot SOF, four-camera and final-health checks.')
