from pathlib import Path
import ast,host,json
here=Path(__file__).resolve().parent
marker=host.PRIVATE/'utc-worker-submitted-private.json';assert not marker.exists(),'Inspect recorded worker; do not repeat'
native="from pathlib import Path; import os; os.umask(0o077); root=Path('/var/lib/samurai'); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes(); (root/'k209-tools').mkdir(mode=0o700)"
host.ssh('python3 -',input=native.encode())
for name in ['loc_nmea.py','pqwm1.py']:
    host.upload(here.parent/'kernel208'/name,'/var/lib/samurai/k209-tools/'+name)
for name in ['clock_uncertainty.py','compare-utc-precision.py']:
    ast.parse((here/name).read_text());host.upload(here/name,'/var/lib/samurai/k209-tools/'+name)
marker.write_text(json.dumps(dict(submissions=1,one_gps_session=True,before_seconds=25,after_seconds=60))+'\n')
p=host.ssh('nohup python3 /var/lib/samurai/k209-tools/compare-utc-precision.py > /var/lib/samurai/k209-utc-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE/'utc-worker-pid-private.txt').write_bytes(p.stdout)
print('One finite UTC precision comparison submitted. Poll the recorded worker; no product program changed.')
