"""Prepare a second post-sensor-switch run and scoped final resource checks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel295'
def stage(s):
 return s.replace('kernel295','kernel296').replace('k295','k296').replace('stage=295','stage=296').replace('kernel_build=295','kernel_build=296').replace("'#295 '","'#296 '")
s=(ROOT/'native-stats.py').read_text().replace('k296-stats-r1','k296-stats-r2')
(ROOT/'native-stats-r2.py').write_text(s);compile(s,'native-stats-r2.py','exec')
s=(ROOT/'poll-stats.py').read_text().replace('k296-stats-r1','k296-stats-r2').replace('stats-launch-private.json','stats-r2-launch-private.json').replace('stats-poll-private.json','stats-r2-poll-private.json').replace('stats-capture-validation.json','stats-r2-capture-validation.json')
(ROOT/'poll-stats-r2.py').write_text(s);compile(s,'poll-stats-r2.py','exec')
s=(ROOT/'analyze-statistics.py').read_text().replace('stats-capture-validation.json','stats-r2-capture-validation.json').replace('k296-stats-r1','k296-stats-r2').replace("f'stats-{frame}-private.qcst'","f'stats-r2-{frame}-private.qcst'").replace('statistics-pixel-validation.json','statistics-r2-pixel-validation.json')
(ROOT/'analyze-statistics-r2.py').write_text(s);compile(s,'analyze-statistics-r2.py','exec')
s=stage((OLD/'final-health.py').read_text())
needle="assert len(prior294_inventory)==778 and prior294_inventory=={str(p.relative_to(prior294)):sha(p) for p in prior294.rglob('*.ko')}"
assert needle in s
s=s.replace(needle,needle+"\nprior295=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k295+')\nprior295_inventory=json.loads((r/'k295-deployment/module-inventory-private.json').read_text())\nassert len(prior295_inventory)==778 and prior295_inventory=={str(p.relative_to(prior295)):sha(p) for p in prior295.rglob('*.ko')}\n")
s=s.replace("['steady_roi_contracts_passed']","['passed']",1)
needle="assert json.loads((ROOT/'optical-pixel-validation.json').read_text())['exposure_response_and_return_passed']"
assert needle in s;s=s.replace(needle,needle+"\nassert json.loads((ROOT/'optical-statistics-validation.json').read_text())['all_packets_valid']\nassert json.loads((ROOT/'statistics-r2-pixel-validation.json').read_text())['passed']")
s=s.replace('standard_bhist_validation_pending=True','standard_bhist_validation_pending=False,standard_bhist_initialization_verified=True,statistics_ready_for_automatic_exposure=False')
s=s.replace('first_statistics_packet_invalid=True','first_statistics_packet_invalid=False,old295_778_modules_preserved=True')
(ROOT/'final-health.py').write_text(s);compile(s,'final-health.py','exec')
print('Prepared second run after wide/tele switch, plus full startup-packet acceptance guards.')
