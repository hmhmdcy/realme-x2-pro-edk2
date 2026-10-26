from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel292/final-health.py').read_text()
s=s.replace('k292-work','k293-work').replace("'#292 '","'#293 '").replace('k292-deployment-r2/module-inventory','k293-deployment/module-inventory')
s=s.replace('stage=292','stage=293').replace('kernel_build=292','kernel_build=293').replace('k292-services-verified','k293-services-verified').replace('k292-tools/final-health','k293-tools/final-health')
needle="assert len(previous_inventory)==778 and previous_inventory=={str(p.relative_to(previous)):sha(p) for p in previous.rglob('*.ko')}"
assert needle in s
s=s.replace(needle,needle+'''
prior292=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k292+')
prior292_inventory=json.loads((r/'k292-deployment-r2/module-inventory-private.json').read_text())
assert len(prior292_inventory)==778 and prior292_inventory=={str(p.relative_to(prior292)):sha(p) for p in prior292.rglob('*.ko')}
''')
s=s.replace('old290_778_modules_preserved=True','old290_778_modules_preserved=True,old292_778_modules_preserved=True')
p=ROOT/'final-health.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared actual k293 and all preserved-release inventory checks.')
