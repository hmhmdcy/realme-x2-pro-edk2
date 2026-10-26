"""Prepare complete current and preserved-release inventory checks after parameter tests."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel291/final-health.py').read_text()
s=s.replace("assert json.loads((ROOT/'physical-pixel-validation.json').read_text())['sensor_pattern_color_contract_passed']","assert json.loads((ROOT/'wb-params-pixel-validation.json').read_text())['all_phase_color_contracts_passed']")
s=s.replace("assert json.loads((ROOT/'tele-pixel-validation.json').read_text())['color_contract_passed']","assert json.loads((ROOT/'optical-pixel-validation.json').read_text())['exposure_response_and_return_passed']")
s=s.replace('k290-work','k292-work').replace("'#290 '","'#292 '").replace('k290-deployment/module-inventory','k292-deployment-r2/module-inventory')
s=s.replace('stage=291','stage=292').replace('kernel_build=290','kernel_build=292').replace('k291-services','k292-services').replace('k291-tools','k292-tools')
needle="assert len(old_inventory)==776 and old_inventory=={str(p.relative_to(old)):sha(p) for p in old.rglob('*.ko')}";assert needle in s
s=s.replace(needle,needle+"""
previous=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k290+')
previous_inventory=json.loads((r/'k290-deployment/module-inventory-private.json').read_text())
assert len(previous_inventory)==778 and previous_inventory=={str(p.relative_to(previous)):sha(p) for p in previous.rglob('*.ko')}
unbooted=r/'k292-deployment/modules-r1-preserved'
unbooted_inventory=json.loads((r/'k292-deployment/module-inventory-private.json').read_text())
assert len(unbooted_inventory)==778 and unbooted_inventory=={str(p.relative_to(unbooted)):sha(p) for p in unbooted.rglob('*.ko')}
""")
s=s.replace('physical_scene_quality_unverified=True','physical_scene_quality_unverified=True,physical_scene_exposure_response_verified=True,standard_wb_params_verified=True,old290_778_modules_preserved=True,unbooted_r1_778_modules_preserved=True')
p=ROOT/'final-health.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared final inventory and preserved release checks.')
