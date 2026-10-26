"""Prepare independent checks for the old boot and the newly deployed release."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel288'
def save(name,s):
 p=ROOT/name;assert not p.exists();compile(s,name,'exec');p.write_text(s)
s=(OLD/'final-health.py').read_text()
s=s.replace("(ROOT/'four-camera-regression-validation.json')","(ROOT.parent/'kernel288/four-camera-regression-validation.json')").replace("(ROOT/'tpg-r3-validation.json')","(ROOT.parent/'kernel288/tpg-r3-validation.json')")
s=s.replace('dict(stage=288','dict(stage=290').replace("ROOT/'final-health-validation.json'","ROOT/'pre-transition-health-validation.json'").replace('final-health-new-boot-private','pre-transition-health-private')
save('pre-transition-health.py',s)
for name in ['native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py','inspect-regression-paths.py']:
 s=(OLD/name).read_text().replace('k288','k290').replace('stage=288','stage=290')
 if name.startswith('native-'):
  needle="assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k290-work/boot-id-private.txt').read_bytes()"
  s=s.replace(needle,needle+"\nassert os.uname().version.startswith('#290 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k290+'")
  s=s.replace("'interrupting-telephoto'","'interrupting-main'")
 save(name,s)
print('Prepared current-boot health and independent new-boot four-camera regression; no device tests submitted.')
