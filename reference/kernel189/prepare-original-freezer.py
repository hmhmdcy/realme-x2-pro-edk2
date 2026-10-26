from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent
text=(ref.parent/'kernel187/test-a11-userspace-trial.sh').read_text()
text=text.replace('k187-a11-userspace','k189-freezer-original').replace('k187-userspace','k189-original-freezer')
text=text.replace('k187-reboot-runtime','k189-reboot-runtime')
text=text.replace('/var/lib/samurai/k187-tools/test-a11-userspace.py','/var/lib/samurai/k189-tools/test-freezer-case.py')
text=text.replace('185 python3','80 python3').replace('timeout -s TERM -k 3 280','timeout -s TERM -k 3 180')
text=text.replace('/tmp/k187-a11-userspace.tar','/tmp/k189-freezer-original.tar')
script=ref/'test-original-freezer.sh';assert not script.exists();script.write_text(text)
subprocess.run(['sh','-n',str(script)],check=True)
host.ssh('test ! -e /var/lib/samurai/k189-tools && mkdir -m700 /var/lib/samurai/k189-tools')
for path in [script,ref/'test-freezer-case.py']:
 dest='/var/lib/samurai/k189-tools/'+path.name;host.upload(path,dest)
 host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
marker=host.PRIVATE/'original-freezer-worker-pid-private.txt';assert not marker.exists()
p=host.ssh("test ! -e /var/lib/samurai/k189-freezer-original && nohup sh /var/lib/samurai/k189-tools/test-original-freezer.sh > /var/lib/samurai/k189-tools/original-freezer-worker-private.log 2>&1 < /dev/null & echo $!")
marker.write_bytes(p.stdout)
print('One original-driver freezer experiment submitted; inspect this worker before further transitions.')
