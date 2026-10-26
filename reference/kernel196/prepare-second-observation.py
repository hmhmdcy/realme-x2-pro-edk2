from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref/'prepare-live-native.py').read_text().replace('k196-live-prepare','k196-live-prepare-r2');(ref/'prepare-live-native-r2.py').write_text(s)
s=(ref/'build-live-overlay.py').read_text().replace('k196-live-prepare/live-input.json','k196-live-prepare-r2/live-input.json').replace('live-input-private.json','live-input-r2-private.json');(ref/'build-live-overlay-r2.py').write_text(s)
s=(ref/'probe-front-driver.py').read_text().replace('k196-front-probe','k196-front-probe-r2').replace('k196-live-prepare/live-input.json','k196-live-prepare-r2/live-input.json')
needle=" time.sleep(1)\n assert (sensor/'driver').resolve().name=='imx471';";assert needle in s
s=s.replace(needle,''' for wait_index in range(12):
  if (sensor/'driver').exists():break
  time.sleep(1)
 deferred=Path('/sys/kernel/debug/devices_deferred');(out/'deferred-private.txt').write_bytes(deferred.read_bytes() if deferred.exists() else b'no debugfs deferred file')
 (out/'sensor-uevent-private.txt').write_bytes((sensor/'uevent').read_bytes())
 report['sensor_links']={p.name:str(p.resolve()) for p in sensor.iterdir() if p.is_symlink()};save()
 assert (sensor/'driver').resolve().name=='imx471';''')
(ref/'probe-front-driver-r2.py').write_text(s)
print('Second observation adds a bounded deferred-probe wait and supplier diagnostics; earlier attempt retained')
