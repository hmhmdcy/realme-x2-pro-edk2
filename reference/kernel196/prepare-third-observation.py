from pathlib import Path
p=Path(__file__).resolve().parent
for source,dest in [('prepare-live-native-r2.py','prepare-live-native-r3.py'),('build-live-overlay-r2.py','build-live-overlay-r3.py'),('probe-front-driver-r2.py','probe-front-driver-r3.py')]:
 s=(p/source).read_text().replace('k196-live-prepare-r2','k196-live-prepare-r3').replace('live-input-r2-private','live-input-r3-private').replace('k196-front-probe-r2','k196-front-probe-r3')
 if source.startswith('probe-'):
  needle="report['resources_applied']=True;save()";assert needle in s;s=s.replace(needle,needle+"\n report['clock_lookup']={p.name:int(p.read_text()) for p in Path('/sys/module/samurai_front_overlay/parameters').iterdir()};save()")
 (p/dest).write_text(s)
s=(p/'finalize-first-attempt.py').read_text().replace("root/'k196-front-probe'","root/'k196-front-probe-r2'");(p/'finalize-second-attempt.py').write_text(s)
print('Third observation records three independent standard clock lookups')
