from pathlib import Path
import json,host
for n in ['summary.json','deferred-private.txt','sensor-uevent-private.txt']:
 try:host.download('/var/lib/samurai/k196-front-probe-r5/'+n,host.PRIVATE/('front-r5-'+n))
 except Exception:continue
r=json.loads((host.PRIVATE/'front-r5-summary.json').read_text());print(json.dumps(dict(keys=list(r),clock_lookup=r.get('clock_lookup'),normal_driver_bound=r.get('normal_driver_bound'),id_accepted=r.get('physical_id_accepted_by_normal_driver'),pm_observations=r.get('pm_observations'),attempts=r.get('attempts'),gpios_after_restore=r.get('gpios_after_restore'),register_restores=r.get('register_restores'))))
