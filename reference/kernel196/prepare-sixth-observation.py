from pathlib import Path
p=Path(__file__).resolve().parent
for source,dest in [('prepare-live-native-r5.py','prepare-live-native-r6.py'),('build-live-overlay-r5.py','build-live-overlay-r6.py'),('probe-front-driver-r5.py','probe-front-driver-r6.py')]:
 s=(p/source).read_text().replace('k196-live-prepare-r5','k196-live-prepare-r6').replace('live-input-r5-private','live-input-r6-private').replace('k196-front-probe-r5','k196-front-probe-r6')
 if source.startswith('probe-'):
  needle="adapter=Path('/sys/bus/i2c/devices/i2c-7/power/runtime_status').read_text().strip()";assert needle in s;s=s.replace(needle,"adapter=Path('/sys/bus/i2c/devices/i2c-7/power/runtime_status').read_text().strip() if Path('/sys/bus/i2c/devices/i2c-7/power/runtime_status').exists() else 'not-exposed'")
  s=s.replace("(out/'genpd-active-private.txt').write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes())", "(out/'genpd-active-private.txt').write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes() if Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').exists() else b'not exposed')")
 (p/dest).write_text(s)
s=(p/'finalize-first-attempt.py').read_text().replace("root/'k196-front-probe'","root/'k196-front-probe-r5'").replace("r['probe_not_bound']=True","r['probe_not_bound']=False").replace('first_attempt_unbound=True','first_attempt_unbound=False');(p/'finalize-fifth-attempt.py').write_text(s)
print('Adapter runtime status is optional in the no-callback I2C adapter; sensor/runtime checks retained')
