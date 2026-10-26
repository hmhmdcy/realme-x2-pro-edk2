from pathlib import Path
ref=Path(__file__).resolve().parent;old=ref.parent/'kernel196'
for name in ['stage-live-tools.py','prepare-live-native-r6.py','build-live-overlay-r6.py']:
 s=(old/name).read_text().replace('k196','k197').replace('stage=196','stage=197')
 if name=='prepare-live-native-r6.py':s=s.replace('/lib/firmware/samurai/k197-front.dtbo','/lib/firmware/samurai/k196-front.dtbo')
 (ref/name.replace('-r6','')).write_text(s)
(ref/'front-probe-overlay.dtso').write_bytes((old/'front-probe-overlay.dtso').read_bytes())
print('Camera setup scripts adapted; original regulator labels and firmware helper filename preserved')
