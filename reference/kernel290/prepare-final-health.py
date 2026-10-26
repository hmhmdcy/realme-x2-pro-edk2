"""Prepare full inventory checks for the new and both preserved previous module trees."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel288/final-health.py').read_text()
s=s.replace("(ROOT/'tpg-r3-validation.json')","(ROOT/'standard-tpg-validation.json')")
s=s.replace('k288-work','k290-work').replace("'#288 '","'#290 '").replace('k288-deployment','k290-deployment').replace('k288-services','k290-services')
s=s.replace('stage=288','stage=290').replace('kernel_build=288','kernel_build=290')
needle="old=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+')"
assert s.count(needle)==1
s=s.replace(needle,"middle=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k279candidate+')\nmiddle_inventory=json.loads((r/'k288-deployment/module-inventory-private.json').read_text())\nassert len(middle_inventory)==778 and middle_inventory=={str(p.relative_to(middle)):sha(p) for p in middle.rglob('*.ko')}\n"+needle)
s=s.replace('old776_modules_preserved=True,','old776_modules_preserved=True,old288_778_modules_preserved=True,')
s=s.replace('hardware_isp_color_correctness_not_verified=True,','hardware_isp_full_color_and_physical_quality_not_yet_complete=True,')
s=s.replace('physical_rotation_and_new_boot_auto_af_not_retested=True)',
 'physical_rotation_and_new_boot_auto_af_not_retested=True,standard_tpg_no_mmio=True)')
p=ROOT/'final-health.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared new-boot full inventory/PM/services checks; no device mutation.')
