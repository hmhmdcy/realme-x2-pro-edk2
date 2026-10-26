from pathlib import Path
import host,json
for name in ['deferred-private.txt','sensor-uevent-private.txt','summary.json','dmesg-after-private.txt']:
 try:host.download('/var/lib/samurai/k196-front-probe-r2/'+name,host.PRIVATE/('front-r2-'+name))
 except Exception:
  if name=='dmesg-after-private.txt':continue
  raise
print((host.PRIVATE/'front-r2-deferred-private.txt').read_text());print((host.PRIVATE/'front-r2-sensor-uevent-private.txt').read_text());r=json.loads((host.PRIVATE/'front-r2-summary.json').read_text());print(json.dumps(dict(sensor_links=r.get('sensor_links'),attempts=r.get('attempts'),gpios_after_restore=r.get('gpios_after_restore'))))
