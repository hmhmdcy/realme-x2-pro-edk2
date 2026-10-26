from pathlib import Path
import ast,json,host

here=Path(__file__).resolve().parent
marker=host.PRIVATE/'debug-worker-r2-submitted-private.json'
assert not marker.exists(),'Inspect recorded worker; do not relaunch'
for name in ['pqwm1.py','capture-debug-nmea-r2.py']:
    ast.parse((here/name).read_text())
    host.upload(here/name,'/var/lib/samurai/k208-loc-tools/'+name)
marker.write_text(json.dumps(dict(submissions=1,duration_seconds=120,temporary_debug_mask=True))+'\n')
p=host.ssh('nohup python3 /var/lib/samurai/k208-loc-tools/capture-debug-nmea-r2.py > /var/lib/samurai/k208-debug-worker-r2-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE/'debug-worker-r2-pid-private.txt').write_bytes(p.stdout)
print('One finite debug-NMEA diagnostic worker submitted. Inspect its recorded PID; do not relaunch.')
