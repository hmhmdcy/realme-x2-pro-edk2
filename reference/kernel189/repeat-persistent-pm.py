from pathlib import Path
import hashlib,json
import host

ref=Path(__file__).resolve().parent;host.transport.PRIVATE=host.PRIVATE/'reboot-r2'
first=json.loads((ref/'persistent-suspend-validation.json').read_text());assert first['suspend_and_sensor_resume_passed']
source=(ref/'test-persistent-suspend.py').read_text()
for index in [2,3]:
 text=source.replace('k189-ssc-pm','k189-ssc-pm-r'+str(index))
 path=ref/('test-persistent-suspend-r'+str(index)+'.py');assert not path.exists();path.write_text(text)
 dest='/var/lib/samurai/k189-tools/'+path.name;host.upload(path,dest)
 host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
marker=host.PRIVATE/'repeat-pm-worker-pid-private.txt';assert not marker.exists()
command="test ! -e /var/lib/samurai/k189-ssc-pm-r2 && test ! -e /var/lib/samurai/k189-ssc-pm-r3 && nohup sh -c 'python3 /var/lib/samurai/k189-tools/test-persistent-suspend-r2.py && python3 /var/lib/samurai/k189-tools/test-persistent-suspend-r3.py; result=$?; printf \"%s\\n\" \"$result\" > /var/lib/samurai/k189-tools/repeat-pm-worker-exit.txt' > /var/lib/samurai/k189-tools/repeat-pm-worker-private.log 2>&1 < /dev/null & echo $!"
p=host.ssh(command);marker.write_bytes(p.stdout)
print('Two sequential PM cycles submitted; the second is skipped if the first fails.')
