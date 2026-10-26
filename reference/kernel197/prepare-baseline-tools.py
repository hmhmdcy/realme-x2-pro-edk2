from pathlib import Path
p=Path(__file__).resolve().parent
for name in ['baseline.py','run-native.py','inspect-live-resources.py','collect-front-before.py']:
 s=(p.parent/'kernel196'/name).read_text().replace('k196-','k197-').replace('stage=196','stage=197');(p/name).write_text(s)
print('Fresh stage197 baseline and resource snapshots prepared')
