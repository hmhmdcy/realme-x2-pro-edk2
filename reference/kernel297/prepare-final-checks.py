"""Prepare validation of the actual extended probe without reusing old acceptances."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=HERE/'analyze-stats-color.py';s=p.read_text();needle='gains[6:8,0]=.25';assert needle in s
s=s.replace(needle,needle+';gains[9:,1]=.25');p.write_text(s)
p=HERE/'analyze-frame-association.py';s=p.read_text()
s=s.replace('for event in completions:', 'for ordinal,event in enumerate(completions):')
s=s.replace("phase=event['phase'];expected=", "phase=event['phase'] if ordinal<7 else 9;expected=")
s=s.replace("rows if r['phase'] in [1,2,3,4,6]", "rows if r['phase'] in [1,2,3,4,6,9]")
p.write_text(s)
s=(HERE.parent/'kernel296/final-health.py').read_text().replace('k296','k297').replace('stage=296','stage=297').replace('kernel_build=296','kernel_build=297').replace("'#296 '","'#297 '")
a=s.index("assert json.loads((ROOT/'four-camera-regression-validation.json')")
b=s.index("code=r'''",a)
s=s[:a]+'''assert json.loads((ROOT/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((ROOT/'stats-pixel-validation.json').read_text())['all_phase_color_contracts_passed']
assert json.loads((ROOT/'sof-association-validation.json').read_text())['shared_sof_contract_passed']
assert json.loads((ROOT/'sof-association-validation.json').read_text())['all_five_observable_roi_transitions_exact']
assert json.loads((ROOT/'optical-pixel-validation.json').read_text())['exposure_response_and_return_passed']
assert json.loads((ROOT/'optical-statistics-validation.json').read_text())['all_packets_valid']
'''+s[b:]
needle="prior295_inventory=json.loads((r/'k295-deployment/module-inventory-private.json').read_text())"
assert needle in s
pos=s.index('\n',s.index('assert len(prior295_inventory)',s.index(needle)))
s=s[:pos]+'''
prior296=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k296+')
prior296_inventory=json.loads((r/'k296-deployment/module-inventory-private.json').read_text())
assert len(prior296_inventory)==778 and prior296_inventory=={str(p.relative_to(prior296)):sha(p) for p in prior296.rglob('*.ko')}
'''+s[pos:]
s=s.replace('first_statistics_packet_invalid=False,','first_statistics_packet_invalid=False,shared_sof_frame_association_verified_in_tested_scope=True,statistics_starvation_sequence_gaps_verified=True,full_statistics_sof_acceptance_passed=False,old296_778_modules_preserved=True,')
p=HERE/'final-health.py';assert not p.exists();p.write_text(s)
for p in HERE.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
print('Prepared WB/ROI scope-aware analysis and final current-boot health checks.')
