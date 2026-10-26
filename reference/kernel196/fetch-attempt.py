from pathlib import Path
import host,json,sys
suffix=sys.argv[1];assert suffix in ['r2','r3','r4']
for name in ['deferred-private.txt','sensor-uevent-private.txt','summary.json']:
 host.download('/var/lib/samurai/k196-front-probe-'+suffix+'/'+name,host.PRIVATE/('front-'+suffix+'-'+name))
r=json.loads((host.PRIVATE/('front-'+suffix+'-summary.json')).read_text());print((host.PRIVATE/('front-'+suffix+'-deferred-private.txt')).read_text());print(json.dumps(dict(clock_lookup=r.get('clock_lookup'),normal_driver_bound=r.get('normal_driver_bound'),pm_observations=r.get('pm_observations'),gpios_after_restore=r.get('gpios_after_restore'))))
